from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid
from typing import Optional

# Clean Architecture Imports
from adapters.redis_lock_adapter import RedisLockAdapter
from adapters.k8s_provisioner_adapter import K8sProvisionerAdapter
from adapters.gui_provisioner_adapter import GuiProvisionerAdapter
from adapters.http_executor_adapter import HttpExecutorAdapter
from services.execution_service import ExecutionService

app = FastAPI(title="ECI Environment Orchestrator")

# Dependency Injection setup
lock_manager = RedisLockAdapter()
provisioners = {
    "algo": K8sProvisionerAdapter(lock_manager=lock_manager),
    "gui": GuiProvisionerAdapter()
}
engine_client = HttpExecutorAdapter()
k8s_manager = ExecutionService(provisioners=provisioners, lock_manager=lock_manager, engine_client=engine_client)

# --- Pydantic Models ---
class ProvisionRequest(BaseModel):
    student_id: uuid.UUID
    course_code: str
    env_type: str
    docker_image: str = "polyglot-cpp-engine:latest"
    is_gui: bool = False

# Add this new model for the execution payload!
class ExecuteRequest(BaseModel):
    pod_name: str
    source_code: str
    stdin_data: Optional[str] = ""
    env_type: str
    is_gui: bool = False

# --- Endpoints ---     
@app.post("/api/v1/orchestrate/provision")
def provision_environment(request: ProvisionRequest):
    try:
        result = k8s_manager.provision_sandbox(
            student_id=str(request.student_id),
            course_code=request.course_code,
            env_type=request.env_type,
            docker_image=request.docker_image,
            is_gui=request.is_gui
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/v1/orchestrate/status/{pod_name}")
def get_sandbox_status(pod_name: str, is_gui: bool = False):
    try:
        ip = k8s_manager.get_pod_ip(pod_name, is_gui=is_gui)
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
            env_type=request.env_type,
            is_gui=request.is_gui
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))