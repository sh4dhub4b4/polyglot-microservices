from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import os,uuid,json,asyncio
import redis.asyncio as redis


router = APIRouter()

# 🚀 HYBRID CLOUD: Use local redis if testing locally, otherwise use K8s internal DNS
REDIS_HOST = os.getenv("REDIS_HOST", "redis-svc.eci-system.svc.cluster.local")
redis_client = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)

@router.websocket("/ws/execute")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    pubsub = None
    task_id = str(uuid.uuid4()) # Unique ID for this specific execution request
    
    try:
        data = await websocket.receive_text()
        payload = json.loads(data)
        
        # Add Task ID to the payload so the Orchestrator knows where to send updates back
        payload["task_id"] = task_id

        # 🚀 Step A: Subscribe to this task's specific live update channel BEFORE queuing
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"task_status_{task_id}")
        
        # Step B: Let frontend know it's in the queue (New Async State)
        await websocket.send_json({"status": "queued", "message": "Request queued securely. Waiting for cluster resources..."})
        
        # 🚀 Step C: Push the task to Redis Queue (Orchestrator will pop this)
        await redis_client.rpush("execution_queue", json.dumps(payload)) # type: ignore
        
        # 🚀 Step D: Listen for live stream updates from Orchestrator via Pub/Sub
        async for message in pubsub.listen():
            if message["type"] == "message":
                update = json.loads(message["data"])
                
                # Forward the EXACT SAME JSON format to the frontend/test-script
                await websocket.send_json(update)
                
                # Break the loop and close if execution is finished or failed
                if update.get("status") in ["completed", "error"]:
                    break

    except WebSocketDisconnect:
        print("Client disconnected")
    finally:
        # Cleanup: Unsubscribe from the channel to save Redis memory
        if pubsub:
            await pubsub.unsubscribe(f"task_status_{task_id}")
            await pubsub.close()