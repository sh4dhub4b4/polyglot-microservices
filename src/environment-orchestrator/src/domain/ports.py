from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import uuid

class ILockManager(ABC):
    @abstractmethod
    def acquire_lock(self, lock_key: str, ttl_seconds: int = 60) -> bool:
        pass

    @abstractmethod
    def release_lock(self, lock_key: str) -> None:
        pass

class ISandboxProvisioner(ABC):
    @abstractmethod
    def provision(self, student_id: uuid.UUID, course_code: str, env_type: str, docker_image: str = "polyglot-cpp-engine:latest", base_cost: float = 1.0, custom_init_script: Optional[str] = None) -> Dict[str, Any]:
        """Returns dict with status, pod_name, source"""
        pass

    @abstractmethod
    def get_pod_ip(self, pod_name: str) -> Optional[str]:
        pass

    @abstractmethod
    def cleanup_pod(self, pod_name: str, keep_alive_for_debug: bool = False) -> None:
        pass

    @abstractmethod
    def extract_postmortem(self, pod_name: str) -> Dict[str, Any]:
        pass

class IEngineClient(ABC):
    @abstractmethod
    def execute_code(self, pod_ip: str, source_code: str, stdin_data: str, env_type: str) -> Dict[str, Any]:
        """Executes code by communicating with the sandbox engine."""
        pass
