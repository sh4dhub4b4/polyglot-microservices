import requests
from typing import Dict, Any
from domain.ports import IEngineClient
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class HttpExecutorAdapter(IEngineClient):
    
    # Circuit Breaker / Retry logic:
    # If the pod is slow to start its internal HTTP server, or if there's a temporary network glitch,
    # retry up to 3 times, with exponential backoff (1s, 2s, 4s).
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        reraise=True
    )
    def execute_code(self, pod_ip: str, source_code: str, stdin_data: str, env_type: str, pod_name: str = None) -> Dict[str, Any]:
        import os
        import socket
        import subprocess
        import time

        is_dev = os.getenv("ENV") == "development"
        host = pod_ip
        port = 8080
        proxy_proc = None

        if is_dev and pod_name:
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
            time.sleep(1.5) # Wait for tunnel to establish

        try:
            print(f"🔌 [Executor] Sending request to sandbox engine at {host}:{port}...")
            sandbox_url = f"http://{host}:{port}/api/v1/execute"
            
            response = requests.post(
                sandbox_url, 
                json={
                    "language": env_type,
                    "source_code": source_code,
                    "stdin_data": stdin_data
                },
                timeout=120
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Sandbox engine returned status {response.status_code}: {response.text}")
        finally:
            if proxy_proc:
                print(f"🛑 [DEV TUNNEL] Closing port-forward for {pod_name}")
                proxy_proc.terminate()
