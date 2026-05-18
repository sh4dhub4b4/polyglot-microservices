from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import httpx
import asyncio

router = APIRouter()

# Internal K8s DNS for the Orchestrator service
ORCHESTRATOR_URL = "http://eci-orchestrator.eci-system.svc.cluster.local:8000/api/v1/orchestrate"

@router.websocket("/ws/execute")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_text()
        payload = json.loads(data)

        # Using httpx for async HTTP requests to the Orchestrator
        async with httpx.AsyncClient(timeout=60.0) as client:
            
            # Phase 1: Provisioning
            await websocket.send_json({"status": "provisioning", "message": "Allocating secure K8s cluster resources..."})
            
            prov_res = await client.post(f"{ORCHESTRATOR_URL}/provision", json={
                "student_id": payload["student_id"],
                "course_code": payload["course_code"],
                "env_type": payload["language"]
            })
            
            if prov_res.status_code != 200:
                await websocket.send_json({"status": "error", "message": f"Provisioning failed: {prov_res.text}"})
                return
                
            prov_data = prov_res.json()
            pod_name = prov_data.get("pod_name")

            # Phase 2: Execution
            await websocket.send_json({"status": "executing", "message": f"Sandbox [{pod_name}] is ready! Injecting payload..."})
            
            exec_res = await client.post(f"{ORCHESTRATOR_URL}/execute", json={
                "pod_name": pod_name,
                "source_code": payload["source_code"],
                "stdin_data": payload.get("stdin_data", ""),
                "env_type":payload["language"]
            })
            
            if exec_res.status_code != 200:
                await websocket.send_json({"status": "error", "message": f"Execution failed: {exec_res.text}"})
                return

            # Phase 3: Completed
            result = exec_res.json()
            result["status"] = "completed"
            await websocket.send_json(result)

    except WebSocketDisconnect:
        print("Client disconnected.")
    except Exception as e:
        await websocket.send_json({"status": "error", "message": str(e)})