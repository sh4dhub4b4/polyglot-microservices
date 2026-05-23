from kubernetes import client, config
from kubernetes.client.rest import ApiException
import uuid
import time
import os
import requests
import redis

class K8sEnvironmentManager:
    """
    Kubernetes-based sandbox environment manager for ECI (Ephemeral Container Instances).
    Eita pre-warmed pod pool manage kore, lease distribute kore, ar execution shesh hole pod cleanup kore.
    """
    
    def __init__(self):
        """
        Initialize K8s client with fallback config strategy.
        Production e in-cluster config use korbe, local dev e kubeconfig file theke load korbe.
        Redis client o initialize kore for distributed locking mechanism.
        """
        try:
            # Production cluster e pod er bhitore theke auto-injected config load kori
            config.load_incluster_config()
            print("Loaded In-Cluster Kubernetes Config")
        except config.ConfigException:
            # Local development ba hybrid testing er jonno ~/.kube/config file theke fallback
            config.load_kube_config()
            print("Loaded Local Kubernetes Config")
        
        # CoreV1Api instance - pod, service, namespace related shob operation er jonno
        self.core_v1 = client.CoreV1Api()
        
        # Dedicated namespace for isolating all sandbox resources
        self.namespace = "eci-sandboxes"
        
        # Redis client setup for distributed lease management
        # Default service DNS use kore Redis cluster e connect kore, env override o allow kore
        redis_host = os.getenv("REDIS_HOST", "redis-svc.eci-system.svc.cluster.local")
        self.redis_client = redis.Redis(
            host=redis_host, 
            port=6379, 
            db=0, 
            decode_responses=True  # Bytes er jaygay string return korbe, readability improve kore
        )

    def provision_sandbox(self, student_id: uuid.UUID, course_code: str, env_type: str) -> dict:
        """
        Smart hybrid provisioner: Pre-warmed pool theke pod lease kore, pool exhausted hole
        dynamically new pod create kore. Future languages add korte shudhu env_mapping update korte hobe.

        Flow:
        1. env_mapping diye alias -> canonical name convert kori
        2. Pre-warmed pool e 3 attempt e lease acquire kori (fast path, ~50ms)
        3. Pool empty hole dynamic pod create kori (slow path, ~5-30s)
        4. Dynamic pod ready na hole cleanup kore Exception raise kori

        Args:
            student_id: Unique student identifier for tracking
            course_code: Course reference code (currently unused, future analytics er jonno)
            env_type: Language/runtime type string (e.g. "java", "c++", "rust")

        Returns:
            dict with keys: status, pod_name, source ("prewarmed_pool" | "dynamic_creation")

        Raises:
            Exception: Invalid env_type, pool exhaustion + dynamic failure, or timeout
        """

        # === Environment Type Routing ===
        # Dictionary-based mapping: easily extendable for new languages without changing logic
        # Format: "alias": "canonical_env_name" (canonical name must match Docker image + K8s label)
        env_mapping = {
            # Native compiled languages -> cpp engine (C, C++, Go, Rust)
            "cpp": "cpp",   "c++": "cpp",   "c": "cpp",
            "go": "cpp",    "golang": "cpp", "rs": "cpp", "rust": "cpp",
            # Scripting languages -> python engine (Python, JS, Node)
            "python": "python", "py": "python", "python3": "python",
            "node": "python",   "javascript": "python", "js": "python",
            # JVM languages -> jvm engine (Java, Kotlin)
            "java": "jvm",   "kotlin": "jvm", "kt": "jvm",
            # .NET languages -> dotnet engine (C#)
            "csharp": "dotnet", "c#": "dotnet",
        }

        mapped_env = env_mapping.get(env_type.lower())
        if not mapped_env:
            raise Exception(f"Unsupported environment type: {env_type}")

        # Engine image convention: eci-{mapped_env}-engine:latest
        # Registry prefix env var theke newa hoy (cloud vs local)
        registry = os.getenv("IMAGE_REGISTRY", "").rstrip("/")
        image_tag = os.getenv("CPP_ENGINE_TAG", "latest")
        image_name = f"eci-{mapped_env}-engine:{image_tag}"
        engine_image = f"{registry}/{image_name}" if registry else image_name

        # ===========================================
        # STEP 1: Try Pre-warmed Pool First (Fast Path)
        # ===========================================
        for attempt in range(3):
            try:
                pods = self.core_v1.list_namespaced_pod(
                    namespace=self.namespace,
                    label_selector=f"app=pre-warmed-sandbox,env_type={mapped_env}"
                )

                for pod in pods.items:
                    # Health check: Running + Ready + Not terminating
                    if (pod.status.phase == "Running" and
                        pod.status.container_statuses and
                        pod.status.container_statuses[0].ready and
                        pod.metadata.deletion_timestamp is None):

                        pod_name = pod.metadata.name
                        lock_key = f"lease:{pod_name}"

                        # Atomic lease acquisition with 60s TTL safety net
                        if self.redis_client.set(lock_key, "leased", ex=60, nx=True):
                            print(f"🔒 [POOL] Leased pre-warmed pod: {pod_name} for student: {student_id}")
                            return {"status": "provisioning", "pod_name": pod_name, "source": "prewarmed_pool"}

            except ApiException as e:
                print(f"Pool query failed (attempt {attempt+1}/3): {e}")

            time.sleep(0.5)

        # ===========================================
        # STEP 2: Dynamic Pod Creation (Slow Fallback)
        # ===========================================
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
                        "app": "dynamic-sandbox",   # Pool theke alada label, mix-up hobe na
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
                    "restartPolicy": "Never"   # One-time use - crash holeo restart korbe na
                }
            }

            self.core_v1.create_namespaced_pod(namespace=self.namespace, body=pod_manifest)
            print(f"🆕 [DYNAMIC] Pod created: {pod_name}, waiting for readiness...")

            # Wait max 30s for dynamic pod to become ready
            for wait_attempt in range(30):
                try:
                    pod = self.core_v1.read_namespaced_pod(name=pod_name, namespace=self.namespace)
                    if (pod.status.phase == "Running" and
                        pod.status.container_statuses and
                        pod.status.container_statuses[0].ready):

                        print(f"✅ [DYNAMIC] Pod ready: {pod_name} (took {wait_attempt+1}s)")
                        self.redis_client.set(f"lease:{pod_name}", "leased", ex=60, nx=True)
                        return {"status": "provisioning", "pod_name": pod_name, "source": "dynamic_creation"}
                except ApiException:
                    pass
                time.sleep(1)

            # 30s geche, pod ready hoy nai - cleanup kore fail kori
            print(f"❌ [DYNAMIC] Pod {pod_name} not ready in 30s, deleting...")
            try:
                self.core_v1.delete_namespaced_pod(name=pod_name, namespace=self.namespace)
            except Exception:
                pass
            raise Exception(f"Dynamic pod creation timeout for env_type: {env_type}")

        except ApiException as e:
            raise Exception(f"Failed to create dynamic pod: {e}")

    def get_pod_ip(self, pod_name: str) -> str:
        """
        Leased pod er internal cluster IP fetch kore for direct HTTP communication.
        
        Pod ready thaklei IP assign hoye thakbe, so pre-warmed pod er jonno instantly return korbe.
        
        Args:
            pod_name: Target pod er name
            
        Returns:
            Pod er ClusterIP string, jeta shudhu cluster er bhitre accessible
        """
        pod = self.core_v1.read_namespaced_pod(name=pod_name, namespace=self.namespace)
        return pod.status.pod_ip
    
    def execute_code(self, pod_name: str, source_code: str, stdin_data: str = "", env_type: str = "") -> dict:
        """
        Main execution handler: Sandbox pod e code pathay, execute kore, then pod destroy kore.
        
        CRITICAL DESIGN PRINCIPLE: 
        Pod ekhane completely ephemeral - use-once-and-destroy pattern follow kore.
        Finally block guarantee kore je execution result success ba failure jai hok, 
        pod delete ar Redis lock release MUST happen for absolute state isolation.
        
        Flow:
        1. Pod IP poll kori (pre-warmed hole instantly pabo)
        2. Minimal boot delay (0.05s, karon server already running)
        3. HTTP POST e code payload forward kori pod er internal API te
        4. FINALLY: Pod delete + lock release - unconditional cleanup
        
        Args:
            pod_name: Leased pod er name
            source_code: Student-er submitted source code
            stdin_data: Standard input data for the program execution
            env_type: Language specifier for engine routing
            
        Returns:
            Sandbox engine er execution result dict (output, errors, execution time etc.)
            
        Note:
            Finally block execute hobei - pod kokhono reuse hobe na, it's absolutely destroyed.
            This is the core of our security isolation model.
        """
        try:
            pod_ip = None
            print(f"k8s->{env_type}Engine:stdin_data {stdin_data}")
            
            # === IP Polling Loop ===
            # Pre-warmed pod er IP already assign thakbe, so first attempt ei pawa uchit
            # Max 10 attempts with 0.1s delay = 1 second timeout for safety
            for _ in range(10):
                pod_ip = self.get_pod_ip(pod_name)
                if pod_ip:
                    break
                time.sleep(0.1)
                
            # IP assignment failed - pod ta corrupted ba networking issue
            if not pod_ip:
                raise Exception(f"Pod {pod_name} did not get an IP in time.")
                
            # === Minimal Boot Delay ===
            # Pre-warmed pod e engine server already running thake on port 8080
            # 50ms delay shudhu TCP connection ready hoar jonno, beshi wait er dorkar nai
            # Traditional cold-start er 2s wait er tulonay etai almost instant
            time.sleep(0.05)

            # === Forward Request to Sandbox Engine ===
            # Pod er internal API endpoint: /api/v1/execute
            # JSON payload e language, source code, ar stdin data pathano hoy
            sandbox_url = f"http://{pod_ip}:8080/api/v1/execute"
            response = requests.post(
                sandbox_url, 
                json={
                    "language": env_type,       # Engine routing er jonno - konta compiler/interpreter use korbe
                    "source_code": source_code, # Raw source code string
                    "stdin_data": stdin_data     # Program er runtime input
                },
                timeout=15  # 15 second timeout - infinite loop ba hang theke protect kore
            )
            
            # Success case - engine execution result ta upstream e forward kori
            if response.status_code == 200:
                return response.json()
            else:
                # Engine internal error - maybe compilation failure, runtime error etc.
                raise Exception(f"Sandbox engine returned status {response.status_code}: {response.text}")
                
        finally:
            # ============================================
            # SMART CLEANUP: Debug Mode vs Normal Mode
            # ============================================
            # DEBUG_MODE=true set thakle ar execution fail korle pod alive rakhi debugging er jonno.
            # Normal mode e absolute state isolation: pod destroy + lock release guaranteed.

            debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
            is_success = False
            try:
                is_success = ('response' in dir() and response is not None and response.status_code == 200)
            except Exception:
                is_success = False

            if debug_mode and not is_success:
                # DEBUG MODE: Pod alive rakhi for manual kubectl exec inspection
                print(f"🛠️ [DEBUG MODE] Execution failed. Pod {pod_name} KEPT ALIVE for debugging!")
                print(f"   👉 Access: kubectl exec -it {pod_name} -n {self.namespace} -- /bin/bash")
                print(f"   👉 Logs  : kubectl logs {pod_name} -n {self.namespace}")
                print(f"   👉 Files : kubectl exec {pod_name} -n {self.namespace} -- cat /tmp/err.txt")
                # Pod e debug label lagiye di - cleanup_debug_pods() diye batch cleanup korte parbo pore
                try:
                    self.core_v1.patch_namespaced_pod(
                        name=pod_name, namespace=self.namespace,
                        body={"metadata": {"labels": {"debug": "true", "debug_time": str(int(time.time()))}}}
                    )
                except Exception:
                    pass
                # Lock release kori jate orchestrator block na thake, but pod survive kore
                try:
                    self.redis_client.delete(f"lease:{pod_name}")
                    print(f"   🔓 Redis lock released, pod preserved for debugging.")
                except Exception as e:
                    print(f"   ⚠️ Redis lock release failed: {e}")
            else:
                # NORMAL MODE: Absolute state isolation - force delete + lock release
                try:
                    print(f"♻️ [CLEANUP] Deleting ephemeral pod: {pod_name}")
                    self.core_v1.delete_namespaced_pod(
                        name=pod_name,
                        namespace=self.namespace,
                        grace_period_seconds=0  # Force immediate deletion, no graceful shutdown
                    )
                except Exception as delete_error:
                    print(f"⚠️ Warning: Failed to delete pod {pod_name}: {delete_error}")

                try:
                    self.redis_client.delete(f"lease:{pod_name}")
                except Exception as redis_error:
                    print(f"⚠️ Warning: Redis cleanup failed for {pod_name}: {redis_error}")

    def cleanup_debug_pods(self, max_age_seconds: int = 3600):
        """
        Stale debug pods clean up kore. CRON job ba scheduler theke call korte hobe.
        Pod e 'debug=true' label thakle ar max_age_seconds er beshi purano hole delete kore.

        Args:
            max_age_seconds: Default 1 hour. Ei age er beshi purano debug pod delete hobe.
        """
        try:
            pods = self.core_v1.list_namespaced_pod(
                namespace=self.namespace,
                label_selector="debug=true"
            )
            current_time = int(time.time())
            cleaned_count = 0

            for pod in pods.items:
                debug_time_label = pod.metadata.labels.get("debug_time", "0")
                debug_time = int(debug_time_label) if debug_time_label.isdigit() else 0

                if (current_time - debug_time) > max_age_seconds:
                    try:
                        self.core_v1.delete_namespaced_pod(name=pod.metadata.name, namespace=self.namespace)
                        cleaned_count += 1
                        print(f"🧹 Cleaned stale debug pod: {pod.metadata.name}")
                    except Exception:
                        pass

            if cleaned_count > 0:
                print(f"✅ Cleaned {cleaned_count} stale debug pod(s).")

        except Exception as e:
            print(f"❌ Debug pod cleanup failed: {e}")
