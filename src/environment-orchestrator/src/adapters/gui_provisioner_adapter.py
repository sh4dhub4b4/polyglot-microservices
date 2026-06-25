import os
import time
import uuid
from typing import Dict, Any, Optional
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream
from domain.ports import ISandboxProvisioner

class GuiProvisionerAdapter(ISandboxProvisioner):
    def __init__(self):
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
            
        self.core_v1 = client.CoreV1Api()
        self.namespace = "eci-sandboxes"

    def _get_dynamic_resources(self, env_type: str) -> dict:
        """Dynamically assign GUI Pod resources. GUI needs more RAM for Xvfb and VNC."""
        env_lower = env_type.lower()
        if "opengl" in env_lower or "cpp" in env_lower:
            return {"requests": {"memory": "256Mi", "cpu": "200m"}, "limits": {"memory": "1Gi", "cpu": "1000m"}}
        elif "java" in env_lower or "android" in env_lower:
            return {"requests": {"memory": "512Mi", "cpu": "500m"}, "limits": {"memory": "2Gi", "cpu": "1500m"}}
        
        # Default fallback for unknown GUI
        return {"requests": {"memory": "512Mi", "cpu": "500m"}, "limits": {"memory": "2Gi", "cpu": "1500m"}}

    def provision(self, student_id: uuid.UUID, course_code: str, env_type: str, docker_image: str = "eci-gui-engine:latest", base_cost: float = 1.0, custom_init_script: Optional[str] = None) -> Dict[str, Any]:
        """
        GUI Pods are Stateful. We first check if the student already has a running GUI pod.
        If yes, we reuse it (Hot-Reloading will handle the rest).
        If no, we spin up a new eci-gui-engine pod.
        """
        # Force GUI image regardless of gateway fallback
        docker_image = "eci-gui-engine:v2_fixed"
        
        registry = os.getenv("IMAGE_REGISTRY", "").rstrip("/")
        
        # WE INTENTIONALLY IGNORE CPP_ENGINE_TAG for GUI because we need to force
        # a cache miss in containerd so it pulls the websocket-fixed image!
        # tag = os.getenv("CPP_ENGINE_TAG", "latest")
        # if tag != "latest":
        #    docker_image = docker_image.replace(":latest", f":{tag}")
            
        engine_image = f"{registry}/{docker_image}" if registry else docker_image
        
        dynamic_resources = self._get_dynamic_resources(env_type)

        # 1. Check if student already has a running GUI pod
        try:
            pods = self.core_v1.list_namespaced_pod(
                namespace=self.namespace,
                label_selector=f"app=gui-sandbox,student_id={student_id}"
            )

            for pod in pods.items:
                if (pod.status.phase == "Running" and
                    pod.status.container_statuses and
                    pod.status.container_statuses[0].ready and
                    pod.metadata.deletion_timestamp is None):
                    
                    print(f"♻️ [GUI POOL] Reusing existing GUI pod for student: {student_id}")
                    return {"status": "provisioning", "pod_name": pod.metadata.name, "source": "existing_stateful", "mapped_env": env_type}
        except ApiException as e:
            print(f"Failed to query existing GUI pods: {e}")

        # 2. Dynamic GUI Pod Creation
        print(f"⚠️ No GUI pod available. Creating dynamic stateful VNC pod...")
        pod_name = f"gui-sandbox-{uuid.uuid4().hex[:8]}"

        try:
            pod_manifest = {
                "apiVersion": "v1",
                "kind": "Pod",
                "metadata": {
                    "name": pod_name,
                    "namespace": self.namespace,
                    "labels": {
                        "app": "gui-sandbox",
                        "env_type": env_type,
                        "student_id": str(student_id)
                    }
                },
                "spec": {
                    "containers": [{
                        "name": f"gui-engine",
                        "image": engine_image,
                        "imagePullPolicy": "IfNotPresent",
                        "ports": [
                            {"containerPort": 8080}, # API Port
                            {"containerPort": 6080}  # noVNC Port
                        ],
                        "livenessProbe": {
                            "tcpSocket": {"port": 8080},
                            "initialDelaySeconds": 5,
                            "periodSeconds": 10
                        },
                        "resources": dynamic_resources
                    }],
                    "restartPolicy": "Never"
                }
            }

            self.core_v1.create_namespaced_pod(namespace=self.namespace, body=pod_manifest)
            print(f"🆕 [GUI DYNAMIC] Pod created: {pod_name}, waiting for readiness...")

            for wait_attempt in range(120):
                try:
                    pod = self.core_v1.read_namespaced_pod(name=pod_name, namespace=self.namespace)
                    if (pod.status.phase == "Running" and
                        pod.status.container_statuses and
                        pod.status.container_statuses[0].ready):

                        print(f"✅ [GUI DYNAMIC] Pod ready: {pod_name} (took {wait_attempt+1}s)")
                        return {"status": "provisioning", "pod_name": pod_name, "source": "dynamic_creation", "mapped_env": env_type}
                except ApiException:
                    pass
                time.sleep(1)

            raise Exception(f"Dynamic GUI pod creation timeout")

        except ApiException as e:
            raise Exception(f"Failed to create GUI pod: {e}")

    def get_pod_ip(self, pod_name: str) -> Optional[str]:
        try:
            pod = self.core_v1.read_namespaced_pod(name=pod_name, namespace=self.namespace)
            return pod.status.pod_ip
        except ApiException:
            return None

    def cleanup_pod(self, pod_name: str, keep_alive_for_debug: bool = False) -> None:
        """
        GUI Pods are Stateful! 
        They DO NOT get cleaned up after a single execution.
        They live until the Scale-to-Zero monitor inside the pod kills it.
        """
        print(f"🛡️ [GUI GUARD] Ignored cleanup for {pod_name}. Pod is managed by Scale-to-Zero monitor.")
        pass

    def extract_postmortem(self, pod_name: str) -> Dict[str, Any]:
        postmortem = {"pod_name": pod_name, "kubernetes_logs": None, "tmp_contents": {}}
        try:
            logs = self.core_v1.read_namespaced_pod_log(name=pod_name, namespace=self.namespace, tail_lines=100)
            postmortem["kubernetes_logs"] = logs
        except Exception as e:
            postmortem["kubernetes_logs"] = f"Failed to fetch logs: {str(e)}"

        try:
            exec_command = ['/bin/sh', '-c', 'echo "--- ls -la /tmp ---" && ls -la /tmp && echo "\\n--- cat /tmp/* ---" && head -n 50 /tmp/* 2>/dev/null']
            resp = stream(self.core_v1.connect_get_namespaced_pod_exec,
                          pod_name,
                          self.namespace,
                          command=exec_command,
                          stderr=True, stdin=False,
                          stdout=True, tty=False)
            postmortem["tmp_contents"]["raw_dump"] = resp
        except Exception as e:
            postmortem["tmp_contents"]["raw_dump"] = f"Failed to exec into pod: {str(e)}"
            
        return postmortem
