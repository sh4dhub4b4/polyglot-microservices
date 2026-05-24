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
    def execute_code(self, pod_ip: str, source_code: str, stdin_data: str, env_type: str) -> Dict[str, Any]:
        print(f"🔌 [Executor] Sending request to sandbox engine at {pod_ip}...")
        sandbox_url = f"http://{pod_ip}:8080/api/v1/execute"
        
        response = requests.post(
            sandbox_url, 
            json={
                "language": env_type,
                "source_code": source_code,
                "stdin_data": stdin_data
            },
            timeout=15
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Sandbox engine returned status {response.status_code}: {response.text}")
