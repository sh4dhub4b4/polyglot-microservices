import os
import json
import time
import asyncio
import redis
import redis.asyncio as aioredis

# Clean Architecture Imports
from adapters.redis_lock_adapter import RedisLockAdapter
from adapters.k8s_provisioner_adapter import K8sProvisionerAdapter
from adapters.gui_provisioner_adapter import GuiProvisionerAdapter
from adapters.http_executor_adapter import HttpExecutorAdapter
from adapters.ws_relay_adapter import WebSocketRelayAdapter
from services.execution_service import ExecutionService

# SRE Note: Worker will use synchronous Redis to match k8s_manager's synchronous flow
REDIS_HOST = os.getenv("REDIS_HOST", "redis-svc.eci-system.svc.cluster.local")
redis_client = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)

# Async Redis client for interactive mode (WebSocket relay needs async I/O)
async_redis_client = aioredis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)

# Dependency Injection setup
lock_manager = RedisLockAdapter()
provisioners = {
    "algo": K8sProvisionerAdapter(lock_manager=lock_manager),
    "gui": GuiProvisionerAdapter()
}
engine_client = HttpExecutorAdapter()
ws_relay = WebSocketRelayAdapter()
k8s_manager = ExecutionService(provisioners=provisioners, lock_manager=lock_manager, engine_client=engine_client)

def publish_status(task_id: str, status: str, message: str, extra: dict = None):
    """Helper function to broadcast messages back to the API Gateway via Pub/Sub"""
    payload = {"status": status, "message": message}
    if extra:
        for k, v in extra.items():
            if k == "status":
                payload["engine_status"] = v
            else:
                payload[k] = v
    redis_client.publish(f"task_status_{task_id}", json.dumps(payload))

def resolve_pod_catalog(task: dict) -> dict:
    """Helper to resolve pod config from Redis Cache (Phase 1.2)"""
    env_type = task.get("env_type", task.get("language", "cpp-basic"))
    
    # Legacy fallback map for backward compatibility with older clients
    legacy_map = {
        "cpp": "cpp-basic",
        "python": "python-ds",
        "java": "java-basic",
        "csharp": "csharp-dotnet",
        "javascript": "node-js",
        "go": "go-sys",
        "rust": "rust-sys",
        "cpp-opengl": "gui-opengl",
        "java-gui": "gui-java"
    }
    if env_type in legacy_map:
        env_type = legacy_map[env_type]
        
    task["env_type"] = env_type
    
    cached_data = redis_client.get(f"pod_catalog:{env_type}")
    if not cached_data:
        raise ValueError(f"Environment '{env_type}' not supported or not found in Pod Catalog.")
        
    pod_cfg = json.loads(cached_data)
    task["docker_image"] = pod_cfg.get("docker_image")
    task["is_gui"] = pod_cfg.get("is_gui", False)
    task["base_cost"] = pod_cfg.get("base_cost", 1.0)
    task["custom_init_script"] = pod_cfg.get("custom_init_script", None)
    return task

def handle_batch_task(task: dict, task_id: str):
    """
    Original batch execution flow (unchanged).
    Used when mode is 'batch' or unspecified.
    Flow: Provision pod → HTTP POST to pod → Collect result → Publish via Redis
    """
    try:
        task = resolve_pod_catalog(task)
    except ValueError as e:
        publish_status(task_id, "error", str(e))
        return

    # Phase 1: Provisioning & Execution
    pod_name = None
    try:
        publish_status(task_id, "provisioning", "Allocating secure K8s cluster resources...")
        prov_res = k8s_manager.provision_sandbox(
            student_id=task["student_id"],
            course_code=task["course_code"],
            env_type=task["env_type"],
            docker_image=task["docker_image"],
            is_gui=task["is_gui"],
            base_cost=task.get("base_cost", 1.0),
            custom_init_script=task.get("custom_init_script", None)
        )
        pod_name = prov_res.get("pod_name")
        
        # Phase 2: Execution
        publish_status(task_id, "executing", f"Sandbox [{pod_name}] is ready! Injecting payload...", extra={"pod_name": pod_name})
        
        # Note: execute_code dynamically routes to the pod and fetches stdout/stderr
        exec_res = k8s_manager.execute_code(
            pod_name=pod_name,
            source_code=task["source_code"],
            stdin_data=task.get("stdin_data", ""),
            env_type=task["env_type"],
            is_gui=task["is_gui"]
        )
        
        exec_res["pod_name"] = pod_name
        
        # Phase 3: Completed
        publish_status(task_id, "completed", "Execution finished successfully", extra=exec_res)
    except Exception as e:
        error_msg = f"Orchestrator error: {str(e)}"
        extra_data = {}
        if pod_name:
            try:
                provisioner = k8s_manager._get_provisioner(task.get("is_gui", False))
                extra_data = {"postmortem_data": provisioner.extract_postmortem(pod_name)}
            except Exception:
                pass
        publish_status(task_id, "error", error_msg, extra=extra_data)
    finally:
        # Cleanup pod
        if pod_name:
            try:
                provisioner = k8s_manager._get_provisioner(task.get("is_gui", False))
                provisioner.cleanup_pod(pod_name, keep_alive_for_debug=False)
                lock_manager.release_lock(f"lease:{pod_name}")
            except Exception:
                pass


async def handle_interactive_task(task: dict, task_id: str):
    """
    New interactive execution flow.
    Used when mode is 'interactive'.
    Flow: Provision pod → WebSocket to pod → Relay stdin/stdout via Redis PubSub
    """
    try:
        task = resolve_pod_catalog(task)

        # Phase 1: Provisioning (reuses the same K8s provisioner)
        publish_status(task_id, "provisioning", "Allocating secure K8s cluster resources...")
        prov_res = k8s_manager.provision_sandbox(
            student_id=task["student_id"],
            course_code=task["course_code"],
            env_type=task["env_type"],
            docker_image=task["docker_image"],
            is_gui=task["is_gui"],
            base_cost=task.get("base_cost", 1.0),
            custom_init_script=task.get("custom_init_script", None)
        )
        pod_name = prov_res.get("pod_name")

        # Phase 2: Get pod IP (with retry, same as ExecutionService)
        pod_ip = None
        for _ in range(10):
            pod_ip = k8s_manager.get_pod_ip(pod_name, is_gui=task.get("is_gui", False))
            if pod_ip:
                break
            await asyncio.sleep(0.1)

        if not pod_ip:
            publish_status(task_id, "error", f"Pod {pod_name} did not get an IP in time.")
            return

        await asyncio.sleep(0.05)  # Brief settle time (same as ExecutionService)

        # Phase 3: Interactive relay via WebSocket
        provisioner = k8s_manager._get_provisioner(task["is_gui"])
        await ws_relay.relay_session(
            pod_ip=pod_ip,
            task_id=task_id,
            payload=task,
            redis_client=async_redis_client,
            provisioner=provisioner,
            pod_name=pod_name
        )

    except ValueError as e:
        publish_status(task_id, "error", str(e))
    except Exception as e:
        error_msg = f"Orchestrator error: {str(e)}"
        extra_data = {}
        if pod_name:
            try:
                # Retrieve the appropriate provisioner to extract logs
                provisioner = k8s_manager._get_provisioner(task.get("is_gui", False))
                extra_data = {"postmortem_data": provisioner.extract_postmortem(pod_name)}
            except Exception:
                pass
        publish_status(task_id, "error", error_msg, extra=extra_data)
    finally:
        # Cleanup pod (interactive mode still needs cleanup)
        if pod_name:
            try:
                provisioner = k8s_manager._get_provisioner(task.get("is_gui", False))
                provisioner.cleanup_pod(pod_name, keep_alive_for_debug=False)
                lock_manager.release_lock(f"lease:{pod_name}")
            except Exception:
                pass


async def run_worker_async():
    print("👷 Orchestrator Worker started. Listening for tasks on 'execution_queue'...")
    
    # Bounded Semaphore to limit concurrent executions (Backpressure)
    MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", "50"))
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    
    async def process_task(task_data: str):
        async with semaphore:
            try:
                task = json.loads(task_data)
                task_id = task.get("task_id")
                
                if not task_id:
                    return
                    
                print(f"📥 Received execution task: {task_id}")
                
                # Route based on execution mode
                mode = task.get("mode", "batch")
                
                if mode == "interactive":
                    print(f"🔌 [INTERACTIVE] Routing task {task_id} to WebSocket relay...")
                    await handle_interactive_task(task, task_id)
                else:
                    print(f"📦 [BATCH] Routing task {task_id} to HTTP executor...")
                    # Since handle_batch_task is synchronous, we run it in a threadpool to not block the async event loop
                    await asyncio.to_thread(handle_batch_task, task, task_id)
                
            except Exception as e:
                error_str = str(e)
                print(f"❌ Error processing task: {error_str}")
                if 'task_id' in locals() and task_id:
                    publish_status(task_id, "error", f"Worker Execution Error: {error_str}")

    while True:
        try:
            # blpop blocks until a new task arrives (Zero CPU waste!)
            # Using async redis client for popping tasks concurrently
            result = await async_redis_client.blpop("execution_queue", timeout=0)
            if not result:
                continue
            
            _, task_data = result
            
            # Fire and forget the task processing to handle multiple tasks concurrently
            asyncio.create_task(process_task(task_data))
            
        except Exception as e:
            print(f"❌ Error in worker main loop: {str(e)}")
            await asyncio.sleep(2) # Cooldown in case of repeated rapid failures

def run_worker():
    asyncio.run(run_worker_async())

if __name__ == "__main__":
    run_worker()