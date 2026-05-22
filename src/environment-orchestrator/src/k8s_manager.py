from kubernetes import client, config
from kubernetes.client.rest import ApiException
import uuid
import time
import os
import requests
import redis

class K8sEnvironmentManager:
    def __init__(self):
        try:
            # Try production cluster config first
            config.load_incluster_config()
            print("Loaded In-Cluster Kubernetes Config")
        except config.ConfigException:
            # Fallback to local Windows config for hybrid testing
            config.load_kube_config()
            print("Loaded Local Kubernetes Config")
        
        self.core_v1 = client.CoreV1Api()
        self.namespace = "eci-sandboxes"
        
        # Initialize Redis client for managing locks
        redis_host = os.getenv("REDIS_HOST", "redis-svc.eci-system.svc.cluster.local")
        self.redis_client = redis.Redis(host=redis_host, port=6379, db=0, decode_responses=True)

    def provision_sandbox(self, student_id: uuid.UUID, course_code: str, env_type: str) -> dict:
        """Leases a ready pre-warmed pod from the pool using Redis distributed locks."""
        
        # Route to either 'cpp' or 'python' engine type
        if env_type.lower() in ["cpp", "c++", "c", "go", "golang", "rust", "rs"]:
            mapped_env = "cpp"
        else:
            mapped_env = "python"
        
        # Retry up to 5 times (5 seconds) if all pods are temporarily leased
        for attempt in range(5):
            try:
                # Query running pods with labels identifying the pre-warmed pool
                pods = self.core_v1.list_namespaced_pod(
                    namespace=self.namespace,
                    label_selector=f"app=pre-warmed-sandbox,env_type={mapped_env}"
                )
                
                for pod in pods.items:
                    # Filter for active, healthy pods
                    if pod.status.phase != "Running":
                        continue
                    if not pod.status.container_statuses or not pod.status.container_statuses[0].ready:
                        continue
                    if pod.metadata.deletion_timestamp is not None:
                        continue
                    
                    pod_name = pod.metadata.name
                    lock_key = f"lease:{pod_name}"
                    
                    # Atomic Redis SET NX EX to claim the lease (60-second expiration safety)
                    if self.redis_client.set(lock_key, "leased", ex=60, nx=True):
                        print(f"🔒 Successfully leased pod: {pod_name} for student: {student_id}")
                        return {"status": "provisioning", "pod_name": pod_name}
                        
            except ApiException as e:
                print(f"Kubernetes API Error during provisioning: {e}")
            
            time.sleep(1)
            
        raise Exception(f"No available pre-warmed sandbox pods for env_type: {env_type}")

    def get_pod_ip(self, pod_name: str) -> str:
        """Fetches the internal cluster IP of the leased pod."""
        pod = self.core_v1.read_namespaced_pod(name=pod_name, namespace=self.namespace)
        return pod.status.pod_ip
    
    def execute_code(self, pod_name: str, source_code: str, stdin_data: str = "", env_type: str = "") -> dict:
        """Sends the payload to the leased pod and guarantees destruction + release."""
        try:
            pod_ip = None
            print(f"k8s->{env_type}Engine:stdin_data {stdin_data}")
            
            # Polling for IP: since the pod is already pre-warmed, this completes instantly
            for _ in range(10):
                pod_ip = self.get_pod_ip(pod_name)
                if pod_ip:
                    break
                time.sleep(0.1)
                
            if not pod_ip:
                raise Exception(f"Pod {pod_name} did not get an IP in time.")
                
            # Boot Delay: reduced from 2s to 0.05s as the engine server is already warm!
            time.sleep(0.05)

            # 3. Forward the code to the sandbox's port 8080
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
                
        finally:
            # 🚀 ABSOLUTE STATE ISOLATION & CLEANUP:
            # Always delete the used pod and release the Redis lease key, even if execution errors out.
            try:
                print(f"♻️ Cleaning up and deleting ephemeral pod: {pod_name}")
                self.core_v1.delete_namespaced_pod(name=pod_name, namespace=self.namespace)
            except Exception as delete_error:
                print(f"Warning: Failed to delete pod {pod_name}: {delete_error}")
            
            try:
                self.redis_client.delete(f"lease:{pod_name}")
            except Exception as redis_error:
                print(f"Warning: Failed to release Redis lock for {pod_name}: {redis_error}")
