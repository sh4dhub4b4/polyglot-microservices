***Role: Architecture Designer & Product Owner***

This is the exact strategic pause we need. Let’s look at the "Curriculum-Aware Academic Cloud Infrastructure" through the lens of a Chief Technology Officer (CTO). We will map out exactly what this beast needs to handle, evaluate our current engineering choices, and define a foolproof pipeline for junior developers to scale it.

---

### 1. The Target Matrix: Languages & Components

To become the "Full Educational Cloud Infrastructure," the platform cannot just be a Python REPL. It must support the entire university curriculum. Here is the operational footprint we are building toward:

#### **A. Target Execution Environments (The "Langs")**

Based on a standard computer science and engineering curriculum, the engine must eventually support:

* **Standard Compute:** Python (Intro to CS, AI/ML), C/C++ (Data Structures, OS), Java (Enterprise Architecture, OOP), Go/Rust (Modern Systems).
* **Web Technologies:** Node.js, HTML/CSS/JS (Web Development).
* **Specialized Workloads:** OpenGL (Computer Graphics), Arduino/Embedded C (IoT & Microcontrollers), R (Data Science).
* **Database Emulation:** SQLite/PostgreSQL isolated instances (Database Management Systems).

#### **B. Core Platform Components (The "Gears")**

* **Identity & Governance:** University hierarchy, RBAC (Role-Based Access Control), Enrollment validation. *(Status: Built via Clean Architecture).*
* **Environment Orchestrator:** Dynamic pod provisioning, K8s networking, lifecycle management. *(Status: Built).*
* **Secure Code Sandbox:** `cgroups` isolation, `setrlimit` resource capping, Privilege dropping (`setuid`). *(Status: Built).*
* **Real-Time Bridge:** WebSocket execution streaming. *(Status: Built).*
* **Academic Workflows:** Assignment templating, automated grading (unit test injection), plagiarism detection (future), practical exam lockdown modes (future).

---

### 2. System Evaluation: Where We Stand

Let's brutally assess the architecture we have engineered so far.

#### **The Strengths (What we got right)**

* **Clean Architecture (The API):** Separating pure Python entities from SQLAlchemy and FastAPI was a masterstroke. If we ever swap PostgreSQL for MongoDB, or FastAPI for Django, the core business rules (`entities.py`, `enroll_student.py`) will not change by a single line of code.
* **True Scalability:** By using Kubernetes to spawn a dedicated ephemeral pod for *every* student, we have eliminated "Noisy Neighbor" problems. If a student writes an infinite loop, it only crashes their specific 128MB pod, not the whole system. Kubernetes handles the scaling automatically.
* **Zero-Trust Security:** Wrapping the C++ execution in native Linux `setrlimit` and dropping root privileges before execution is enterprise-grade. This is how platforms like LeetCode and HackerRank protect their servers.

#### **The Weaknesses & Maintenance Risks**

* **Docker Image Bloat:** If we pack Python, C++, Java, Node, and OpenGL into a single Docker image for the Sandbox, that image will be 5GB+. Pulling a 5GB image every time a student hits "Run" will cause massive latency.
* *Future Fix:* We will need specific Docker images (e.g., `eci-sandbox-python:latest`, `eci-sandbox-java:latest`) and update the Orchestrator to pull the correct one.


* **C++ Complexity:** The Secure Sandbox is written in C++ using raw Linux system calls (`fork`, `execl`). This is incredibly fast but very hostile to junior developers. A single memory leak or unhandled exception here brings down the sandbox.

---

### 3. The "Noob's Guide" to Adding a New Language

Because we used the **Strategy Design Pattern** in Phase 5, adding a new language (like Java or Node.js) does not require rewriting the core system. A junior developer only needs to touch three specific files.

Here is the exact Step-by-Step SOP (Standard Operating Procedure) for adding a new language (e.g., **Java**):

#### **Step 1: Install the Runtime in Docker**

The container needs the actual language installed.

* **File to touch:** `docker/runtime/Dockerfile.cpp-engine`
* **Action:** Add the installation command for the new language.
```dockerfile
# Example addition
RUN apt-get update && apt-get install -y default-jdk

```



#### **Step 2: Create the Language Strategy (C++)**

Thanks to the **Template Method Pattern**, we have hidden all the complex OS-level code (`fork`, `execvp`, POSIX pipes, and security restrictions) inside `BaseStrategy.hpp`. You only need to provide the paths and commands!

* **File to touch:** `src/cpp-processing-engine/src/JavaStrategy.hpp` (New File)
* **Action:** Inherit from `BaseStrategy` and implement the 3 protected configuration methods.
```cpp
#pragma once
#include "BaseStrategy.hpp"

class JavaStrategy : public BaseStrategy {
protected:
    std::string get_source_file_path() const override { return "/tmp/Main.java"; }
    
    std::vector<std::string> get_compile_command() const override {
        return {"javac", "/tmp/Main.java"};
    }
    
    std::vector<std::string> get_execute_command() const override {
        return {"java", "-Xmx128m", "-Xms32m", "-XX:+UseSerialGC", "-cp", "/tmp", "Main"};
    }
};
```



#### **Step 3: Register the Strategy in the Orchestrator (C++)**

The C++ server needs to know this new strategy exists.

* **File to touch:** `src/cpp-processing-engine/src/SandboxOrchestrator.hpp`
* **Action:** Add an `else if` statement to connect the API request to the new strategy.
```cpp
#include "JavaStrategy.hpp" // Add this

void set_language(const std::string& language) {
    if (language == "python") {
        strategy = std::make_unique<PythonStrategy>();
    } else if (language == "java") {
        strategy = std::make_unique<JavaStrategy>(); // Add this
    } else {
        throw std::invalid_argument("Unsupported runtime environment.");
    }
}

```



**That is it.** Because of the modular architecture, the Python API Gateway, the WebSocket streamer, and the Kubernetes orchestrator do not need to be touched. The junior developer updates the Sandbox, rebuilds the Docker image, and the whole platform suddenly supports Java.