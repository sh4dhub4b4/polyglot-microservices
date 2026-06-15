import os
import time
import json
from typing import Dict, Any, Optional
from domain.ports import ISandboxProvisioner, IEngineClient, ILockManager

class ExecutionService:
    def __init__(
        self, 
        provisioners: Dict[str, ISandboxProvisioner], 
        lock_manager: ILockManager, 
        engine_client: IEngineClient
    ):
        self.provisioners = provisioners
        self.lock_manager = lock_manager
        self.engine_client = engine_client

    def _get_provisioner(self, is_gui: bool = False) -> ISandboxProvisioner:
        if is_gui:
            return self.provisioners["gui"]
        return self.provisioners["algo"]

    def provision_sandbox(self, student_id: str, course_code: str, env_type: str, docker_image: str = "polyglot-cpp-engine:latest", is_gui: bool = False, base_cost: float = 1.0, custom_init_script: Optional[str] = None) -> Dict[str, Any]:
        provisioner = self._get_provisioner(is_gui)
        return provisioner.provision(student_id, course_code, env_type, docker_image=docker_image, base_cost=base_cost, custom_init_script=custom_init_script)
        
    def get_pod_ip(self, pod_name: str, is_gui: bool = False) -> Optional[str]:
        provisioner = self._get_provisioner(is_gui)
        return provisioner.get_pod_ip(pod_name)
        
    def execute_code(self, pod_name: str, source_code: str, stdin_data: str, env_type: str, is_gui: bool = False) -> Dict[str, Any]:
        provisioner = self._get_provisioner(is_gui)
        try:
            pod_ip = None
            for _ in range(10):
                pod_ip = provisioner.get_pod_ip(pod_name)
                if pod_ip:
                    break
                time.sleep(0.1)
                
            if not pod_ip:
                raise Exception(f"Pod {pod_name} did not get an IP in time.")
                
            time.sleep(0.05)
            
            result = self.engine_client.execute_code(pod_ip, source_code, stdin_data, env_type, pod_name=pod_name)
            is_success = True
            return result
        except Exception as e:
            is_success = False
            # Generate Postmortem Report
            postmortem_data = provisioner.extract_postmortem(pod_name)
            error_payload = {
                "message": str(e),
                "postmortem_data": postmortem_data
            }
            raise Exception(json.dumps(error_payload))
        finally:
            debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
            keep_alive = debug_mode and not is_success
            
            provisioner.cleanup_pod(pod_name, keep_alive_for_debug=keep_alive)
            self.lock_manager.release_lock(f"lease:{pod_name}")
