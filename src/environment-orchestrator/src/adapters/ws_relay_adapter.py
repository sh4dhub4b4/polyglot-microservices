import asyncio
import json
import websockets
import redis.asyncio as aioredis
import os
from typing import Dict, Any

# SRE Note: This adapter requires the 'websockets' package (already used in test_e2e_gauntlet.py)

REDIS_HOST = os.getenv("REDIS_HOST", "redis-svc.eci-system.svc.cluster.local")


class WebSocketRelayAdapter:
    """
    Interactive execution adapter that opens a WebSocket to the C++ engine pod
    and relays stdin/stdout/stderr between Redis PubSub and the child process.

    This replaces HttpExecutorAdapter for interactive mode. Instead of a single
    HTTP POST → Response cycle, it maintains a persistent WebSocket connection
    to stream I/O in real-time.

    Redis Channels:
      - task_status_{task_id}  : Worker → Gateway (stdout/stderr/status updates)
      - task_stdin_{task_id}   : Gateway → Worker (user input from frontend)

    Architecture:
      Frontend ←WS→ API Gateway ←Redis PubSub→ Worker ←WS→ C++ Engine Pod
    """

    async def relay_session(
        self,
        pod_ip: str,
        task_id: str,
        payload: Dict[str, Any],
        redis_client: aioredis.Redis,
        provisioner: Any,
        pod_name: str
    ) -> None:
        import os
        import subprocess
        import socket
        
        is_dev = os.getenv("ENV") == "development"
        host = pod_ip
        port = 8080
        proxy_proc = None

        if is_dev:
            # Dynamically bind a port for proxying Windows Host -> K8s Pod
            s = socket.socket()
            s.bind(('', 0))
            port = s.getsockname()[1]
            s.close()
            host = "127.0.0.1"
            
            print(f"🚇 [DEV TUNNEL] Port-forwarding {pod_name}:8080 -> localhost:{port}")
            proxy_proc = subprocess.Popen(
                ["kubectl", "port-forward", f"pod/{pod_name}", f"{port}:8080", "-n", "eci-sandboxes"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            await asyncio.sleep(1.5) # Wait for tunnel to establish

        ws_url = f"ws://{host}:{port}/ws/execute"
        pubsub = redis_client.pubsub()
        completed = asyncio.Event()

        # Wait for engine port to be ready before WebSocket connect
        ws = None
        try:
            max_port_wait = 15
            for attempt in range(max_port_wait):
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(0.5)
                    s.connect((host, port))
                    s.close()
                    break
                except (ConnectionRefusedError, OSError):
                    if attempt == max_port_wait - 1:
                        raise Exception(f"Pod {pod_name} engine port {port} not ready after {max_port_wait * 0.5}s")
                    await asyncio.sleep(0.5)

            ws = await websockets.connect(ws_url, open_timeout=10)

            # ── Step 1: Send initial payload to the pod ──
            # GUI engines expect the full pod_catalog ID (e.g. "gui-opengl"),
            # non-GUI engines expect the base language name (e.g. "cpp")
            lang = payload.get("env_type") if payload.get("is_gui") else payload.get("engine_language", payload.get("env_type", payload.get("language")))
            initial_msg = {
                "language": lang,
                "source_code": payload["source_code"],
            }
            if "files" in payload:
                initial_msg["files"] = payload["files"]
            if "stdin_data" in payload and payload["stdin_data"]:
                initial_msg["stdin_data"] = payload["stdin_data"]
            await ws.send(json.dumps(initial_msg))

            # ── Step 2: Subscribe to stdin channel for this task ──
            stdin_channel = f"task_stdin_{task_id}"
            await pubsub.subscribe(stdin_channel)

            # ── Step 2b: Inform gateway that sandbox is executing (Fully Subscribed) ──
            await redis_client.publish(
                f"task_status_{task_id}",
                json.dumps({
                    "status": "executing",
                    "message": f"Sandbox [{pod_name}] is ready! Starting interactive session...",
                    "pod_name": pod_name
                })
            )

            async def forward_pod_output():
                """Reads from pod WS and publishes to Redis (→ API Gateway → Frontend)."""
                try:
                    async for message in ws:
                        data = json.loads(message)
                        status = data.get("status")

                        # Forward every message to the API Gateway via Redis PubSub
                        await redis_client.publish(
                            f"task_status_{task_id}",
                            json.dumps(data)
                        )

                        # Check for terminal states
                        if status in ["completed", "compile_error", "timeout", "error"]:
                            completed.set()
                            return
                except websockets.exceptions.ConnectionClosed:
                    await redis_client.publish(
                        f"task_status_{task_id}",
                        json.dumps({
                            "status": "error",
                            "message": "Pod WebSocket connection closed unexpectedly."
                        })
                    )
                    completed.set()

            async def forward_user_stdin():
                """Reads from Redis PubSub (← API Gateway ← Frontend) and writes to pod WS."""
                try:
                    async for message in pubsub.listen():
                        if completed.is_set():
                            return

                        if message["type"] == "message":
                            # Forward the stdin payload directly to the pod
                            await ws.send(message["data"])
                except Exception as e:
                    print(f"[WS Relay] stdin forwarding error: {e}")

            # ── Step 3: Run both forwarding tasks concurrently ──
            output_task = asyncio.create_task(forward_pod_output())
            stdin_task = asyncio.create_task(forward_user_stdin())

            # Wait for the process to complete (or timeout)
            try:
                await asyncio.wait_for(completed.wait(), timeout=120)
            except asyncio.TimeoutError:
                postmortem_data = provisioner.extract_postmortem(pod_name)
                await redis_client.publish(
                    f"task_status_{task_id}",
                    json.dumps({
                        "status": "error",
                        "message": "Interactive session timed out (120s max).",
                        "postmortem_data": postmortem_data
                    })
                )

            # Cleanup concurrent tasks
            stdin_task.cancel()
            try:
                await stdin_task
            except asyncio.CancelledError:
                pass

            await output_task

        except (websockets.exceptions.WebSocketException, ConnectionRefusedError, OSError) as e:
            # Pod connection failure — publish error back to the API Gateway
            await redis_client.publish(
                f"task_status_{task_id}",
                json.dumps({
                    "status": "error",
                    "message": f"Failed to connect to pod WebSocket: {e}",
                    "postmortem_data": provisioner.extract_postmortem(pod_name)
                })
            )
        finally:
            if proxy_proc:
                print(f"🛑 [DEV TUNNEL] Closing port-forward for {pod_name}")
                proxy_proc.terminate()
            if ws is not None:
                try:
                    await ws.close()
                except Exception:
                    pass
            # Cleanup Redis subscription
            await pubsub.unsubscribe(f"task_stdin_{task_id}")
            await pubsub.close()
