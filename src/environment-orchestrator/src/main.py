from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid
from k8s_manager import K8sEnvironmentManager
from typing import Optional

app = FastAPI(title="ECI Environment Orchestrator")
k8s_manager = K8sEnvironmentManager()

# --- Pydantic Models ---
class ProvisionRequest(BaseModel):
    student_id: uuid.UUID
    course_code: str
    env_type: str

# Add this new model for the execution payload!
class ExecuteRequest(BaseModel):
    pod_name: str
    source_code: str
    stdin_data: Optional[str] = ""
    env_type: str

# --- Endpoints ---     
@app.post("/api/v1/orchestrate/provision")
def provision_environment(request: ProvisionRequest):
    try:
        result = k8s_manager.provision_sandbox(
            student_id=request.student_id,
            course_code=request.course_code,
            env_type=request.env_type
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/v1/orchestrate/status/{pod_name}")
def get_sandbox_status(pod_name: str):
    try:
        ip = k8s_manager.get_pod_ip(pod_name)
        if ip:
            return {"status": "ready", "ip": ip}
        return {"status": "pending", "ip": None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add this entirely NEW endpoint!
@app.post("/api/v1/orchestrate/execute")
def execute_code(request: ExecuteRequest):
    try:
        # Ask K8sManager to execute the code inside the specific pod
        # Note: Ensure your k8s_manager actually has a method named 'execute_code' 
        # or update this method name to match whatever you named it in k8s_manager.py
        print(f"main.py->k8s:stdin_data {request.stdin_data}")
        result = k8s_manager.execute_code(
            pod_name=request.pod_name,
            source_code=request.source_code,
            stdin_data=request.stdin_data,
            env_type=request.env_type
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))