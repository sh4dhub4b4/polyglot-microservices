# Polyglot Microservices Platform

An industry-grade, highly scalable code execution and Capture The Flag (CTF) platform. This system utilizes a secure microservices architecture to dynamically spin up isolated, resource-constrained execution environments on demand using Kubernetes.

## 🎯 Core Vision Review
The objective of this platform is to provide a zero-trust, high-performance backend capable of executing untrusted code safely. By leveraging a microservices architecture, the system guarantees that the web frontend, the API routing layer, and the execution layer remain strictly decoupled. The eventual integration with a modern Next.js frontend will provide a seamless, real-time feedback loop for users interacting with code challenges or security environments.

## 🏗️ System Architecture

* **API Gateway (FastAPI):** Acts as the ingress controller, managing WebSocket connections and routing execution payloads.
* **Environment Orchestrator (FastAPI):** Authenticates with the Kubernetes Control Plane using RBAC ServiceAccounts to dynamically provision isolated Pods.
* **Secure Execution Sandbox (C++ / Ubuntu):** An immutable container that drops root privileges (`setuid`), restricts system resources (`setrlimit`), and executes untrusted code natively.
* **Infrastructure (Kubernetes):** Manages the lifecycle, networking, and DNS resolution of all microservices.

## 🐛 Bug Ledger & Fixing Methodology

Throughout the development and integration lifecycle, several critical architectural boundaries were identified and resolved. 

### 1. The "Walled Garden" DNS Disconnect
* **Symptom:** `[Errno 11001] getaddrinfo failed` and K8s internal IP routing failures.
* **Root Cause:** Running microservices on a hybrid environment (Host OS Windows vs. K8s Subnet). Windows cannot natively resolve K8s internal DNS (CoreDNS) or route to `10.244.x.x` IPs.
* **Resolution:** Enforced strict "Local = Production" parity. All APIs were containerized and deployed *inside* the Kubernetes cluster using `Deployment` and `Service` manifests, ensuring native internal Service Mesh communication.

### 2. The Sandbox "Silent Death" (exit_code: 1)
* **Symptom:** C++ sandbox returned `exit_code: 1` with completely empty stdout/stderr payloads when attempting to execute Python scripts.
* **Root Cause:** Twofold error in system calls:
    1.  The `exec` command utilized a non-existent binary path (`/usr/local/bin/python3`).
    2.  The parent process failed to read the redirected file descriptors after the child process crashed.
* **Resolution:** Patched `PythonStrategy.hpp` to utilize the absolute APT path (`/usr/bin/python3`), catch all `errno` signals via `strerror(errno)`, and forcefully read the output text buffers regardless of the child's exit state.

### 3. The Virtual Memory Choke
* **Symptom:** Python interpreter failed to boot entirely, resulting in immediate segmentation faults.
* **Root Cause:** `RLIMIT_AS` was restricted to 128MB. Modern Python 3 requires >200MB of virtual address space simply to map shared C libraries and the dynamic linker.
* **Resolution:** Increased the virtual memory limit (`MAX_MEMORY_MB`) to 512MB in `SecurityContainer.hpp` to allow the interpreter to initialize, while retaining strict CPU time limitations.

## 🚀 Deployment Instructions

1.  Build the C++ Sandbox Engine:
    `docker build -t eci-cpp-engine:latest -f docker/runtime/Dockerfile.cpp-engine .`
2.  Build the Microservices:
    `docker build -t eci-api-gateway:latest -f src/api-gateway/Dockerfile src/api-gateway/`
    `docker build -t eci-orchestrator:latest -f src/environment-orchestrator/Dockerfile src/environment-orchestrator/`
3.  Deploy to Kubernetes:
    `kubectl apply -f k8s/eci-cluster-deployment.yaml`

---