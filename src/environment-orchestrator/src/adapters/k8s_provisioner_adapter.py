import os
import time
import uuid
from typing import Dict, Any, Optional
from kubernetes import client, config
from kubernetes.client.rest import ApiException
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

    def provision(self, student_id: uuid.UUID, course_code: str, env_type: str) -> Dict[str, Any]:
        env_mapping = {
            "cpp": "cpp", "c++": "cpp", "c": "cpp",
            "go": "cpp", "golang": "cpp", "rs": "cpp", "rust": "cpp",
            "python": "python", "py": "python", "python3": "python",
            "node": "python", "javascript": "python", "js": "python",
            "java": "jvm", "kotlin": "jvm", "kt": "jvm",
            "csharp": "dotnet", "c#": "dotnet",
        }

        mapped_env = env_mapping.get(env_type.lower())
        if not mapped_env:
            raise Exception(f"Unsupported environment type: {env_type}")

        registry = os.getenv("IMAGE_REGISTRY", "").rstrip("/")
        image_tag = os.getenv("CPP_ENGINE_TAG", "latest")
        image_name = f"eci-{mapped_env}-engine:{image_tag}"
        engine_image = f"{registry}/{image_name}" if registry else image_name

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
                        "ports": [{"containerPort": 8080}],
                        "livenessProbe": {
                            "tcpSocket": {"port": 8080},
                            "initialDelaySeconds": 5,
                            "periodSeconds": 10,
                            "timeoutSeconds": 3,
                            "failureThreshold": 3
                        },
                        "resources": {
                            "requests": {"memory": "64Mi", "cpu": "20m"},
                            "limits":   {"memory": "256Mi", "cpu": "500m"}
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

            self.core_v1.create_namespaced_pod(namespace=self.namespace, body=pod_manifest)
            print(f"🆕 [DYNAMIC] Pod created: {pod_name}, waiting for readiness...")

            for wait_attempt in range(30):
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

            print(f"❌ [DYNAMIC] Pod {pod_name} not ready in 30s, deleting...")
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
