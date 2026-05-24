import os
import time
from typing import Dict, Any, Optional
from domain.ports import ISandboxProvisioner, IEngineClient, ILockManager

class ExecutionService:
    def __init__(
        self, 
        provisioner: ISandboxProvisioner, 
        lock_manager: ILockManager, 
        engine_client: IEngineClient
    ):
        self.provisioner = provisioner
        self.lock_manager = lock_manager
        self.engine_client = engine_client

    def provision_sandbox(self, student_id: str, course_code: str, env_type: str) -> Dict[str, Any]:
        return self.provisioner.provision(student_id, course_code, env_type)
        
    def get_pod_ip(self, pod_name: str) -> Optional[str]:
        return self.provisioner.get_pod_ip(pod_name)
        
    def execute_code(self, pod_name: str, source_code: str, stdin_data: str, env_type: str) -> Dict[str, Any]:
        try:
            pod_ip = None
            for _ in range(10):
                pod_ip = self.provisioner.get_pod_ip(pod_name)
                if pod_ip:
                    break
                time.sleep(0.1)
                
            if not pod_ip:
                raise Exception(f"Pod {pod_name} did not get an IP in time.")
                
            time.sleep(0.05)
            
            result = self.engine_client.execute_code(pod_ip, source_code, stdin_data, env_type)
            is_success = True
            return result
        except Exception as e:
            is_success = False
            raise e
        finally:
            debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
            keep_alive = debug_mode and not is_success
            
            self.provisioner.cleanup_pod(pod_name, keep_alive_for_debug=keep_alive)
            self.lock_manager.release_lock(f"lease:{pod_name}")
