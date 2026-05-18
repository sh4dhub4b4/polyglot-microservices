from kubernetes import client, config
from kubernetes.client.rest import ApiException
import uuid
import time,os
import requests

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

    def provision_sandbox(self, student_id: uuid.UUID, course_code: str, env_type: str) -> dict:
        """Dynamically spins up a secure C++ sandbox pod for a specific student."""
        
        engine_tag = os.getenv("CPP_ENGINE_TAG", "latest")
        # 🚀 SRE Dynamic Image Routing!
        if env_type.lower() in ["cpp", "c++", "c"]:
            dynamic_image = f"eci-cpp-engine:{engine_tag}"
        else:
            dynamic_image = f"eci-python-engine:{engine_tag}" # Default lightweight image
        
        pod_name = f"sandbox-{course_code.lower()}-{str(student_id)[:8]}"
        
        container = client.V1Container(
            name="secure-engine",
            image=dynamic_image,             # 👈 ডাইনামিক ইমেজ ভ্যারিয়েবল!
            image_pull_policy="IfNotPresent",      # 👈 'Never' দিলে কুবারনেটস বাধ্য হয়ে লোকাল ইমেজটাই নেবে
            ports=[client.V1ContainerPort(container_port=8080)],
            resources=client.V1ResourceRequirements(
                requests={"memory": "128Mi", "cpu": "250m"},
                limits={"memory": "256Mi", "cpu": "500m"}
            )
        )

        # Define the Pod metadata and spec
        pod = client.V1Pod(
            api_version="v1",
            kind="Pod",
            metadata=client.V1ObjectMeta(
                name=pod_name,
                labels={
                    "app": "sandbox",
                    "student_id": str(student_id),
                    "course_code": course_code,
                    "env_type": env_type
                }
            ),
            spec=client.V1PodSpec(
                containers=[container],
                restart_policy="Never" # Sandboxes are ephemeral
            )
        )

        try:
            # Tell Kubernetes to create the Pod
            self.core_v1.create_namespaced_pod(namespace=self.namespace, body=pod)
            return {"status": "provisioning", "pod_name": pod_name}
        except ApiException as e:
            raise Exception(f"Exception when calling CoreV1Api->create_namespaced_pod: {e}")

    def get_pod_ip(self, pod_name: str) -> str:
        """Fetches the internal cluster IP of the pod so the API Gateway can route code to it."""
        pod = self.core_v1.read_namespaced_pod(name=pod_name, namespace=self.namespace)
        return pod.status.pod_ip
    
    # pyrefly: ignore [parse-error]
    def execute_code(self, pod_name: str, source_code: str, stdin_data: str = "", env_type: str ="") -> dict:
        """Fetches the Pod IP and sends the code directly to the Sandbox Engine."""
        pod_ip = None
        
        print(f"k8s->cppEngine:stdin_data {stdin_data}")
        # 1. Wait for Kubernetes to assign an IP to the Pod (Polling)
        for _ in range(30):
            pod_ip = self.get_pod_ip(pod_name)
            if pod_ip:
                break
            time.sleep(1)
            
        if not pod_ip:
            raise Exception(f"Pod {pod_name} did not get an IP in time.")
            
        # 2. Give the sandbox engine a second to boot its internal server
        time.sleep(2)

        # 3. Forward the code to the sandbox's port 8080
        sandbox_url = f"http://{pod_ip}:8080/api/v1/execute"
        try:
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
                
        except Exception as e:
            raise Exception(f"Failed to communicate with sandbox at {pod_ip}: {str(e)}")