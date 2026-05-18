
# 📚 ECI Platform: Integration & Debugging Post-Mortem

**System:** Polyglot Microservices Platform (Phase 6 - Orchestrator & Sandbox)
**Environment:** Windows Host (WSL2) + Docker Desktop Kubernetes (K8s)

## 1. The Bug Compendium (Root Causes & Resolutions)

During the integration of the local API Gateway, the K8s Orchestrator, and the C++ Docker Sandbox, we encountered **7 distinct architectural friction points**.

| # | Error Signature | Root Cause | The Fix |
| --- | --- | --- | --- |
| **1** | `ModuleNotFoundError: fastapi / kubernetes` | **Nested Virtual Environments.** `uv` created local `.venv` folders inside the microservice directories, but the terminal was bound to the root `.venv`. | Standardized on the root `.venv`. Ran `uv pip install` centrally and used Uvicorn's `--app-dir src` flag to map the pathing. |
| **2** | `HTTP 404` on WebSocket Route | **Windows DNS Resolution.** Calling `localhost` on Windows sometimes routes to IPv6 (`::1`) or the Docker bridge, stripping the WS `Upgrade` headers. | Bypassed Windows DNS by hardcoding the IPv4 loopback address: `ws://127.0.0.1:8000/ws/execute`. |
| **3** | `Could not connect to C++ Sandbox` | **Missing Artifact.** The C++ engine was never compiled into an executable or packaged into a container. | Created a Multi-Stage Dockerfile (`Dockerfile.cpp-engine`) to compile the C++ inside an Ubuntu image. |
| **4** | `fatal error: httplib.h: No such file` | **Missing Dependencies.** C++ single-header libraries were not pushed to the repo, breaking the Docker CI/CD build. | Injected `wget` into the Dockerfile Builder stage to pull headers directly from GitHub during compilation. |
| **5** | `[Errno 11001] getaddrinfo failed` | **Service Mesh Disconnect.** Gateway tried to route to `http://environment-orchestrator:8000` (K8s Internal DNS), but the Gateway was running on Windows, not in K8s. | Temporarily hardcoded the Orchestrator URL to `http://127.0.0.1:8001` for local host-to-host testing. |
| **6** | `Could not route traffic` to `10.244.x.x` | **The Walled Garden.** K8s assigned an internal subnet IP to the Pod. Windows host OS physically cannot route POST requests to a K8s internal IP without a proxy. | Dropped a manual tunnel through the K8s wall using `kubectl port-forward` to hit the Pod directly. |
| **7** | `exit_code: 1` (Silent Failure) | **Container Permissions & Naming.** Ubuntu 22.04 lacks a `python` command (it uses `python3`), and the unprivileged `sandboxuser` lacked write permissions to the `/app` root. | Added `python-is-python3` alias and `chmod 777 /app` to the Stage 2 Dockerfile to allow native execution. |

---

## 2. Technical Debt: Production-Grade Bypasses

To validate the C++ execution logic without spending weeks configuring local network proxies, we intentionally bypassed several "Production-Grade" configurations.

**Before we deploy this to AWS/GCP, we MUST revert these bypasses:**

### ⚠️ Bypass 1: Microservices running on Host OS (Windows)

* **What we did:** We ran the API Gateway and Orchestrator using `uvicorn` in Windows PowerShell.
* **Production Standard:** Both Python services must be containerized (`Dockerfile.gateway`, `Dockerfile.orchestrator`) and deployed *inside* the K8s cluster alongside the Sandboxes. This completely eliminates Bugs #5 and #6 because all services share the K8s internal DNS (CoreDNS).

### ⚠️ Bypass 2: Over-permissive Container Rights

* **What we did:** We ran `RUN chmod 777 /app` in the Dockerfile so the Python script could be temporarily saved.
* **Production Standard:** `777` gives read/write/execute permissions to everyone. In production, we should create a dedicated `/app/temp` folder owned specifically by `sandboxuser` with `700` permissions.

### ⚠️ Bypass 3: Port-Forwarding for E2E Tests

* **What we did:** We manually tunneled `kubectl port-forward` and used PowerShell `Invoke-RestMethod` to bypass the API Gateway's failure to reach `10.244.x.x`.
* **Production Standard:** End-to-End tests should hit the API Gateway's public Ingress IP, and K8s internal routing handles the hop to the Pod natively.

---

## 3. The Microservices Networking Decision Tree

Use this logic tree for future debugging when Service A cannot talk to Service B.

```text
[Request Fails: Connection Refused / Timeout / 404]
   │
   ├─ Q1: Are both services running on the SAME network plane?
   │    ├─ NO (e.g., Service A on Windows, Service B in K8s)
   │    │   ├─ Diagnose: "Walled Garden" Boundary Issue.
   │    │   └─ Fix: Use `kubectl port-forward` OR move Service A into K8s.
   │    │
   │    └─ YES (Both in Windows, or Both in K8s)
   │        └─ Go to Q2.
   │
   ├─ Q2: How are they addressing each other?
   │    ├─ Using `localhost`
   │    │   ├─ Diagnose: Inside a Docker container, `localhost` means the container itself, not the sibling container.
   │    │   └─ Fix: Use the Container Name or K8s Service Name.
   │    │
   │    ├─ Using K8s Service Name (e.g., `environment-orchestrator`)
   │    │   ├─ Diagnose: CoreDNS failure or Service not exposed.
   │    │   └─ Fix: Verify Service exists (`kubectl get svc`).
   │    │
   │    └─ Using IPv4 Loopback (`127.0.0.1`)
   │        └─ Go to Q3.
   │
   └─ Q3: Is the receiving framework intercepting it correctly?
        ├─ Diagnose: Uvicorn/FastAPI might be expecting WS but got HTTP.
        └─ Fix: Check Uvicorn terminal logs for incoming protocol headers.

```

---

### *A Note on Your Last Terminal Output*

If you are still seeing `exit_code: 1` in your terminal right now, it means one of two things:

1. The new Docker image didn't finish building before you re-ran it.
2. The old broken pod wasn't fully deleted, and the port-forward tunnel reconnected to the old broken container.

*(If you want to clear that final hurdle, delete all pods again, ensure the build is 100% complete, and re-run the port-forward!)*

