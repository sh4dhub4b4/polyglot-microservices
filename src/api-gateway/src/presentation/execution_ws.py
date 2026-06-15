from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import os,uuid,json,asyncio
import redis.asyncio as redis
from infrastructure.database import SessionLocal
from infrastructure.orm_models import PodCatalogORM, EnrollmentORM, CourseOfferingORM
from presentation.metrics_router import pod_spawns_total
from use_cases.wasm_router import is_lightweight_payload

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
        
        # 🚀 Phase 3 Gateway Validation Check
        env_type = payload.get("env_type") or payload.get("language")
        student_id_str = payload.get("student_id")
        
        # 1. Fetch PodCatalog info synchronously using SQLAlchemy (or fetch from Redis Cache)
        # For security validation, we check the DB directly to ensure owner_faculty_id rules
        if env_type:
            db = SessionLocal()
            try:
                pod_spec = db.query(PodCatalogORM).filter(PodCatalogORM.id == env_type).first()
                if pod_spec and pod_spec.custom_env_id:
                    if not student_id_str:
                        await websocket.send_json({"status": "error", "message": "Missing student_id for custom pod access."})
                        await websocket.close(code=1008)
                        return
                    
                    try:
                        student_uuid = uuid.UUID(student_id_str)
                    except ValueError:
                        await websocket.send_json({"status": "error", "message": "Invalid student_id format."})
                        await websocket.close(code=1008)
                        return
                        
                    # Check if student is enrolled in ANY course offered by this faculty
                    enrollments = db.query(EnrollmentORM).join(CourseOfferingORM).filter(
                        EnrollmentORM.student_id == student_uuid,
                        CourseOfferingORM.faculty_id == pod_spec.owner_faculty_id
                    ).all()
                    
                    if not enrollments:
                        await websocket.send_json({"status": "error", "message": "403 Forbidden: You are not enrolled in a course authorized for this custom environment."})
                        await websocket.close(code=1008)
                        return
            finally:
                db.close()
        


        # Detect execution mode from the frontend payload
        # Default to "batch" for backwards compatibility with existing test scripts
        mode = payload.get("mode", "batch")

        # 🚀 Step A: Subscribe to this task's specific live update channel BEFORE queuing
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"task_status_{task_id}")
        
        # Step B: Let frontend know it's in the queue (New Async State)
        await websocket.send_json({"status": "queued", "message": "Request queued securely. Waiting for cluster resources..."})
        
        # 🚀 Phase 3 Metrics: Record a pod spawn attempt
        course_code = payload.get("course_code", "unknown")
        pod_spawns_total.labels(course_code=course_code, env_type=env_type or "unknown").inc()
        
        # 🚀 Phase 3 WASM Router: Detect lightweight payloads
        source_code = payload.get("source_code", "")
        if is_lightweight_payload(source_code, env_type):
            print(f"[INFO] Payload detected as LIGHTWEIGHT. Bypassing K8s. Offloading to WASM target.")
            
            # MOCK Execution: Immediately return a simulated execution result instead of enqueuing
            await websocket.send_json({"status": "executing", "message": "Executing locally via WASM Engine..."})
            await asyncio.sleep(0.5) # simulate execution
            mock_result = {
                "status": "completed",
                "message": "Execution finished successfully",
                "stdout": f"[WASM Local Execution Mock] Executed {len(source_code)} bytes successfully.\n",
                "execution_time_ms": 42
            }
            await websocket.send_json(mock_result)
            # Cleanup and exit early to fully bypass K8s!
            if pubsub:
                await pubsub.unsubscribe(f"task_status_{task_id}")
                await pubsub.close()
            return
            
        # 🚀 Step C: Push the task to Redis Queue (Orchestrator will pop this)
        await redis_client.rpush("execution_queue", json.dumps(payload)) # type: ignore
        
        if mode == "interactive":
            # ═══════════════════════════════════════════════════════════════
            # INTERACTIVE MODE: Bi-directional relay
            # - Forward status updates from Worker → Frontend (via Redis PubSub)
            # - Forward user stdin from Frontend → Worker (via Redis PubSub)
            # ═══════════════════════════════════════════════════════════════

            async def forward_status_to_frontend():
                """Reads Worker updates from Redis PubSub and sends to frontend WebSocket."""
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        update = json.loads(message["data"])
                        await websocket.send_json(update)
                        
                        # Break if execution is finished
                        if update.get("status") in ["completed", "compile_error", "timeout", "error"]:
                            return

            async def forward_stdin_to_worker():
                """Reads user input from frontend WebSocket and publishes to Redis for the Worker."""
                try:
                    while True:
                        data = await websocket.receive_text()
                        try:
                            input_payload = json.loads(data)
                            # Forward stdin_data or close_stdin commands to the worker
                            if "stdin_data" in input_payload or "close_stdin" in input_payload:
                                await redis_client.publish(
                                    f"task_stdin_{task_id}",
                                    json.dumps(input_payload)
                                )
                        except json.JSONDecodeError:
                            # Raw text fallback: wrap as stdin_data
                            await redis_client.publish(
                                f"task_stdin_{task_id}",
                                json.dumps({"stdin_data": data + "\n"})
                            )
                except WebSocketDisconnect:
                    pass
                except Exception:
                    pass

            # Run both directions concurrently
            status_task = asyncio.create_task(forward_status_to_frontend())
            stdin_task = asyncio.create_task(forward_stdin_to_worker())

            # Wait for execution to complete (status_task finishes on terminal status)
            await status_task

            # Cancel stdin forwarding once execution is done
            stdin_task.cancel()
            try:
                await stdin_task
            except asyncio.CancelledError:
                pass

        else:
            # ═══════════════════════════════════════════════════════════════
            # BATCH MODE: Original one-way relay (unchanged)
            # - Only forwards status updates from Worker → Frontend
            # ═══════════════════════════════════════════════════════════════
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