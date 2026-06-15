import time
import json
from locust import HttpUser, task, between, events
import websocket # requires websocket-client

class PolyglotStudentUser(HttpUser):
    wait_time = between(1, 5) # Students wait 1-5 seconds between actions
    
    @task(3)
    def check_health(self):
        """Simulate frequent checks to the health/status endpoint."""
        self.client.get("/health", name="API Gateway Health")

    @task(1)
    def simulate_workspace_execution(self):
        """Simulate a student opening a workspace and executing code via WebSockets."""
        ws_url = self.host.replace("http", "ws") + "/ws/execution"
        
        start_time = time.time()
        try:
            ws = websocket.create_connection(ws_url)
            
            payload = {
                "command": "execute",
                "language": "cpp",
                "code": "#include <iostream>\\nint main() { std::cout << \\"Load Test\\"; return 0; }",
                "userId": "locust_user"
            }
            ws.send(json.dumps(payload))
            
            # Wait for execution response
            result = ws.recv()
            
            total_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="WebSocket",
                name="Execute Code (C++)",
                response_time=total_time,
                response_length=len(result),
                exception=None,
            )
            ws.close()
            
        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="WebSocket",
                name="Execute Code (C++)",
                response_time=total_time,
                response_length=0,
                exception=e,
            )
