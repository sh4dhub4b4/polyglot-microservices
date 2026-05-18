```mermaid
gantt
    title ECI Platform - Execution Roadmap
    dateFormat  YYYY-MM-DD
    
    section Phase 1-5: Core & Sandbox
    Docker, K8s, Clean Arch       :done,    core1, 2026-05-01, 10d
    C++ Secure Sandbox Interfaces :done,    sand1, 2026-05-11, 4d

    section Phase 6: Orchestrator
    K8s Dynamic Provisioning      :done,    orch1, 2026-05-15, 1d
    WebSocket Streaming           :done,    orch2, after orch1, 1d
    Tech Debt: C++ Dockerization  :done,    orch3, 2026-05-17, 1d
    Tech Debt: K8s Service Mesh   :done,    orch4, after orch3, 1d

    section Phase 7: Web UI
    Next.js Frontend              :active,  ui1, 2026-05-18, 5d
```