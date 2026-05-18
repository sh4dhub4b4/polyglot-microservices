# QA & Developer Testing Validation Guide

This guide provides step-by-step validation protocols for junior developers and QA testers to verify the system infrastructure.

---

## Test 1: AI Worker Smoke Test (Local Development)

**1. Purpose:** Ensure the Python AI worker container builds successfully, boots up, and exposes its health endpoint without crashing.

**2. Setup Instructions:**
1. Open your terminal.
2. Navigate to the project root directory.
3. Run the following command exactly as written:
   `docker compose -f compose/docker-compose.dev.yml up -d --build`

**3. Expected Result:**
The terminal will download packages and display `[+] Running X/X`. Finally, it should say `Started` for the `dev-workspace` or `ai-worker` service. 

**4. Verification Checkpoint:**
Run this command in your terminal:
`curl http://localhost:8000/health`

**Expected Output:**
`{"status": "healthy"}`

**5. Common Failure Cases:**
* **Error:** `bind: address already in use` 
  * *Why:* Another application is using port 8000.
* **Error:** `Connection refused`
  * *Why:* The container crashed immediately after starting.

**6. Troubleshooting Steps:**
1. Check running containers: `docker ps`
2. If the container is missing, check the crash logs: `docker logs <container_name>`
3. Look for Python tracebacks like `ModuleNotFoundError` or `SyntaxError`.

**7. Pass/Fail Criteria:**
* **PASS:** The `curl` command returns a 200 OK status with the JSON healthy payload within 10 seconds.
* **FAIL:** Timeout, Connection Refused, or an HTTP 500 status code.

---

## Test 2: Infrastructure Resource Limits Verification

**1. Purpose:**
Verify that the production containers respect the CPU and Memory limits defined in our architecture to prevent system starvation.

**2. Setup Instructions:**
1. Run the production compose file:
   `docker compose -f compose/docker-compose.prod.yml up -d`

**3. Verification Checkpoint:**
Run the Docker stats command to view active resource constraints:
`docker stats --no-stream`

**4. Expected Result:**
Look at the `LIMIT` column. The AI worker should show a memory limit of `4GiB` and the C++ engine should show `2GiB`.

**5. Pass/Fail Criteria:**
* **PASS:** Limits match the production configuration exactly.
* **FAIL:** Memory limits show `0B` or the maximum RAM of your host machine (indicating no constraints were applied).