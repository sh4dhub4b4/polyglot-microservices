import os
import uuid
from typing import Dict, Any, Optional
from domain.ports import ISandboxProvisioner, ILockManager

class LocalProvisionerAdapter(ISandboxProvisioner):
    def __init__(self, lock_manager: ILockManager):
        self.lock_manager = lock_manager
        self.engine_port = int(os.getenv("LOCAL_ENGINE_PORT", "8080"))

    def provision(self, student_id: uuid.UUID, course_code: str, env_type: str,
                  docker_image: str = "", base_cost: float = 1.0,
                  custom_init_script: Optional[str] = None) -> Dict[str, Any]:
        pod_name = f"local-{env_type}-{uuid.uuid4().hex[:8]}"
        self.lock_manager.acquire_lock(f"lease:{pod_name}", ttl_seconds=60)
        print(f"🏠 [LOCAL] Using local engine for {env_type} (pod_name={pod_name})")
        return {"status": "provisioning", "pod_name": pod_name,
                "source": "local_engine", "mapped_env": env_type}

    def get_pod_ip(self, pod_name: str) -> Optional[str]:
        return "127.0.0.1"

    def cleanup_pod(self, pod_name: str, keep_alive_for_debug: bool = False) -> None:
        self.lock_manager.release_lock(f"lease:{pod_name}")

    def extract_postmortem(self, pod_name: str) -> Dict[str, Any]:
        return {"pod_name": pod_name, "note": "local engine — no postmortem"}
