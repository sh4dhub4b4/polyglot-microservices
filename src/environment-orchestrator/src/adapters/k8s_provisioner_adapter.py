import os
import time
import uuid
from typing import Dict, Any, Optional
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream
from domain.ports import ISandboxProvisioner, ILockManager

class K8sProvisionerAdapter(ISandboxProvisioner):
    def __init__(self, lock_manager: ILockManager):
        self.lock_manager = lock_manager
        try:
            config.load_incluster_config()
            print("Loaded In-Cluster Kubernetes Config")
        except config.ConfigException:
            config.load_kube_config()
            print("Loaded Local Kubernetes Config")
        
        self.core_v1 = client.CoreV1Api()
        self.namespace = "eci-sandboxes"

    def _get_dynamic_resources(self, env_type: str, base_cost: float = 1.0) -> dict:
        """Dynamically assign Pod resources based on language and base_cost to cut down cluster usage."""
        env_lower = env_type.lower()
        if any(env_lower.startswith(prefix) for prefix in ["cpp", "c", "wasm"]):
            return {"requests": {"memory": "32Mi", "cpu": "10m"}, "limits": {"memory": "128Mi", "cpu": "200m"}}
        elif any(env_lower.startswith(prefix) for prefix in ["rust", "go"]):
            return {"requests": {"memory": "64Mi", "cpu": "20m"}, "limits": {"memory": "256Mi", "cpu": "500m"}}
        elif any(env_lower.startswith(prefix) for prefix in ["python", "node"]):
            return {"requests": {"memory": "128Mi", "cpu": "50m"}, "limits": {"memory": "512Mi", "cpu": "1000m"}}
        elif any(env_lower.startswith(prefix) for prefix in ["java", "csharp", "dotnet"]):
            return {"requests": {"memory": "256Mi", "cpu": "100m"}, "limits": {"memory": "1Gi", "cpu": "1500m"}}
        
        if base_cost > 1.0:
            # Scale up limits linearly based on custom base_cost (e.g. 2.0x cost = 2x resources)
            # Memory string manipulation (e.g., "128Mi" -> "256Mi")
            pass # Keep it simple for now or implement full scaling

        # Default fallback
        return {"requests": {"memory": "64Mi", "cpu": "20m"}, "limits": {"memory": "256Mi", "cpu": "500m"}}

    def provision(self, student_id: uuid.UUID, course_code: str, env_type: str, docker_image: str = "polyglot-cpp-engine:latest", base_cost: float = 1.0, custom_init_script: Optional[str] = None) -> Dict[str, Any]:
        # env_type now directly corresponds to PodCatalog ID (e.g., 'cpp-basic', 'python-ds')
        mapped_env = env_type.lower()
        
        registry = os.getenv("IMAGE_REGISTRY", "").rstrip("/")
        tag = os.getenv("CPP_ENGINE_TAG", "latest")
        if ":latest" in docker_image and tag != "latest":
            docker_image = docker_image.replace(":latest", f":{tag}")
            
        engine_image = f"{registry}/{docker_image}" if registry else docker_image

        # Calculate dynamic resource limits
        dynamic_resources = self._get_dynamic_resources(mapped_env, base_cost)

        # 1. Try Pre-warmed Pool First (Fast Path)
        for attempt in range(3):
            try:
                pods = self.core_v1.list_namespaced_pod(
                    namespace=self.namespace,
                    label_selector=f"app=pre-warmed-sandbox,env_type={mapped_env}"
                )

                for pod in pods.items:
                    if (pod.status.phase == "Running" and
                        pod.status.container_statuses and
                        pod.status.container_statuses[0].ready and
                        pod.metadata.deletion_timestamp is None):

                        pod_name = pod.metadata.name
                        lock_key = f"lease:{pod_name}"

                        if self.lock_manager.acquire_lock(lock_key, ttl_seconds=60):
                            print(f"🔒 [POOL] Leased pre-warmed pod: {pod_name} for student: {student_id}")
                            return {"status": "provisioning", "pod_name": pod_name, "source": "prewarmed_pool", "mapped_env": mapped_env}

            except ApiException as e:
                print(f"Pool query failed (attempt {attempt+1}/3): {e}")

            time.sleep(0.5)

        # 2. Dynamic Pod Creation (Slow Fallback)
        print(f"⚠️ No pre-warmed pod available for '{mapped_env}'. Creating dynamic pod...")
        pod_name = f"sandbox-{mapped_env}-{uuid.uuid4().hex[:8]}"

        try:
            pod_manifest = {
                "apiVersion": "v1",
                "kind": "Pod",
                "metadata": {
                    "name": pod_name,
                    "namespace": self.namespace,
                    "labels": {
                        "app": "dynamic-sandbox",
                        "env_type": mapped_env,
                        "created_by": "provisioner",
                        "student_id": str(student_id)
                    }
                },
                "spec": {
                    "containers": [{
                        "name": f"engine-{mapped_env}",
                        "image": engine_image,
                        "imagePullPolicy": "IfNotPresent",
                        "resources": dynamic_resources,
                        "securityContext": {
                            "runAsUser": 10002,
                            "runAsGroup": 10002,
                            "runAsNonRoot": True,
                            "allowPrivilegeEscalation": False,
                            "readOnlyRootFilesystem": True,
                            "seccompProfile": {
                                "type": "RuntimeDefault"
                            }
                        },
                        "volumeMounts": [{"mountPath": "/tmp", "name": "ram-disk"}]
                    }],
                    "volumes": [{
                        "name": "ram-disk",
                        "emptyDir": {"medium": "Memory"}
                    }],
                    "restartPolicy": "Never"
                }
            }

            if custom_init_script:
                print(f"🛠️ [CUSTOM] Injecting custom init_script for {mapped_env}")
                pod_manifest["spec"]["initContainers"] = [{
                    "name": f"init-{mapped_env}",
                    "image": engine_image,
                    "command": ["/bin/sh", "-c"],
                    "args": [f"{custom_init_script} || echo 'Init Script Failed but Continuing'"],
                    "volumeMounts": [{"mountPath": "/tmp", "name": "ram-disk"}]
                }]

            self.core_v1.create_namespaced_pod(namespace=self.namespace, body=pod_manifest)
            print(f"🆕 [DYNAMIC] Pod created: {pod_name}, waiting for readiness...")

            for wait_attempt in range(25):
                try:
                    pod = self.core_v1.read_namespaced_pod(name=pod_name, namespace=self.namespace)
                    if (pod.status.phase == "Running" and
                        pod.status.container_statuses and
                        pod.status.container_statuses[0].ready):

                        print(f"✅ [DYNAMIC] Pod ready: {pod_name} (took {wait_attempt+1}s)")
                        self.lock_manager.acquire_lock(f"lease:{pod_name}", ttl_seconds=60)
                        return {"status": "provisioning", "pod_name": pod_name, "source": "dynamic_creation", "mapped_env": mapped_env}
                except ApiException:
                    pass
                time.sleep(1)

            print(f"❌ [DYNAMIC] Pod {pod_name} not ready in 25s, deleting...")
            try:
                self.core_v1.delete_namespaced_pod(name=pod_name, namespace=self.namespace)
            except Exception:
                pass
            raise Exception(f"Dynamic pod creation timeout for env_type: {env_type}")

        except ApiException as e:
            raise Exception(f"Failed to create dynamic pod: {e}")

    def get_pod_ip(self, pod_name: str) -> Optional[str]:
        try:
            pod = self.core_v1.read_namespaced_pod(name=pod_name, namespace=self.namespace)
            return pod.status.pod_ip
        except ApiException:
            return None

    def cleanup_pod(self, pod_name: str, keep_alive_for_debug: bool = False) -> None:
        if keep_alive_for_debug:
            print(f"🛠️ [DEBUG MODE] Pod {pod_name} KEPT ALIVE for debugging!")
            try:
                self.core_v1.patch_namespaced_pod(
                    name=pod_name, namespace=self.namespace,
                    body={"metadata": {"labels": {"debug": "true", "debug_time": str(int(time.time()))}}}
                )
            except Exception:
                pass
        else:
            try:
                print(f"♻️ [CLEANUP] Deleting ephemeral pod: {pod_name}")
                self.core_v1.delete_namespaced_pod(
                    name=pod_name,
                    namespace=self.namespace,
                    grace_period_seconds=0
                )
            except Exception as delete_error:
                print(f"⚠️ Warning: Failed to delete pod {pod_name}: {delete_error}")

    def extract_postmortem(self, pod_name: str) -> Dict[str, Any]:
        postmortem = {"pod_name": pod_name, "kubernetes_logs": None, "tmp_contents": {}}
        try:
            # 1. Fetch Pod Logs
            logs = self.core_v1.read_namespaced_pod_log(name=pod_name, namespace=self.namespace, tail_lines=100)
            postmortem["kubernetes_logs"] = logs
        except Exception as e:
            postmortem["kubernetes_logs"] = f"Failed to fetch logs: {str(e)}"

        try:
            # 2. Exec into pod and fetch /tmp contents
            # Using head -n 50 to avoid massive output, but show enough to diagnose
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
