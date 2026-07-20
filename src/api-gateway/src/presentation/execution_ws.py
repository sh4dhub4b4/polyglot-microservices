from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import os,uuid,json,asyncio,time
import redis.asyncio as redis
from infrastructure.database import SessionLocal
from infrastructure.orm_models import PodCatalogORM, EnrollmentORM, CourseOfferingORM, TenantORM, BillingTransactionORM, UserORM
from presentation.metrics_router import pod_spawns_total
from use_cases.wasm_router import is_lightweight_payload
from use_cases.local_executor import execute_local
from use_cases.auth_service import decode_access_token
from uuid6 import uuid7

router = APIRouter()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

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
        
        # ═══════════════════════════════════════════════════════════════
        # JWT Validation — extract verified student_id from token
        # ═══════════════════════════════════════════════════════════════
        ENV = os.getenv("ENV", "production")
        token = payload.get("token")
        jwt_payload = decode_access_token(token) if token else None

        if ENV == "development" and not jwt_payload:
            # ponytail: dev bypass — skip JWT, use payload student_id or default
            student_id_str = payload.get("student_id", "00000000-0000-0000-0000-000000000000")
            payload["student_id"] = student_id_str
        elif not jwt_payload:
            await websocket.send_json({"status": "error", "message": "Authentication required. Provide a valid token."})
            await websocket.close(code=1008)
            return
        else:
            student_id_str = jwt_payload.get("sub")
            if jwt_payload.get("role") != "STUDENT":
                await websocket.send_json({"status": "error", "message": "Only students can execute code."})
                await websocket.close(code=1008)
                return
            # Override payload with verified student_id (trust the token, not user input)
            payload["student_id"] = student_id_str
        
        # 🚀 Phase 3 Gateway Validation Check
        env_type = payload.get("env_type") or payload.get("language")
        
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
        
        # 🚀 Phase 3 WASM Router: Detect lightweight payloads → execute locally
        # Set SKIP_LIGHTWEIGHT=1 to force all execution through K8s (for debugging)
        source_code = payload.get("source_code", "")
        skip_lightweight = os.getenv("SKIP_LIGHTWEIGHT", "0") == "1"
        if not skip_lightweight and mode != "interactive" and is_lightweight_payload(source_code, env_type):
            print(f"[INFO] Lightweight payload detected. Executing locally, bypassing K8s.")
            await websocket.send_json({"status": "executing", "message": "Executing locally..."})
            
            stdin_input = payload.get("stdin_data", "")
            exec_time_ms = 0
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, execute_local, source_code, env_type, stdin_input)
                exec_time_ms = result.execution_time_ms
                await websocket.send_json({
                    "status": "completed",
                    "message": "Execution finished successfully (local)",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.exit_code,
                    "execution_time_ms": exec_time_ms,
                })
            except Exception as e:
                await websocket.send_json({
                    "status": "error",
                    "message": f"Local execution failed: {e}",
                })
            
            _deduct_credits(student_id_str, env_type, task_id, exec_time_ms)
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

            last_update = None

            async def forward_status_to_frontend():
                """Reads Worker updates from Redis PubSub and sends to frontend WebSocket."""
                nonlocal last_update
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        update = json.loads(message["data"])
                        last_update = update
                        try:
                            await websocket.send_json(update)
                        except WebSocketDisconnect:
                            return
                        except Exception:
                            return

                        if update.get("status") in ["completed", "compile_error", "timeout", "error"]:
                            return

            async def forward_stdin_to_worker():
                """Reads user input from frontend WebSocket and publishes to Redis for the Worker."""
                try:
                    while True:
                        data = await websocket.receive_text()
                        try:
                            input_payload = json.loads(data)
                            if "stdin_data" in input_payload or "close_stdin" in input_payload:
                                await redis_client.publish(
                                    f"task_stdin_{task_id}",
                                    json.dumps(input_payload)
                                )
                        except json.JSONDecodeError:
                            await redis_client.publish(
                                f"task_stdin_{task_id}",
                                json.dumps({"stdin_data": data + "\n"})
                            )
                except WebSocketDisconnect:
                    print("[INTERACTIVE] Client disconnected, sending cancel signal to worker.")
                    await redis_client.publish(
                        f"task_stdin_{task_id}",
                        json.dumps({"close_stdin": True})
                    )
                except Exception:
                    pass

            # Run both directions concurrently
            status_task = asyncio.create_task(forward_status_to_frontend())
            stdin_task = asyncio.create_task(forward_stdin_to_worker())

            # Wait for execution to complete (status_task finishes on terminal status)
            try:
                await status_task
            except (WebSocketDisconnect, Exception):
                pass

            stdin_task.cancel()
            try:
                await stdin_task
            except asyncio.CancelledError:
                pass

            if last_update and last_update.get("status") in ["completed"]:
                exec_time_ms = last_update.get("execution_time_ms", 500.0)
                _deduct_credits(student_id_str, env_type, task_id, exec_time_ms)

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
                        # 💳 Billing: Deduct compute credits on successful execution
                        exec_time_ms = update.get("execution_time_ms", 500.0)
                        _deduct_credits(student_id_str, env_type, task_id, exec_time_ms)
                        break

    except WebSocketDisconnect:
        print("Client disconnected")
    finally:
        # Cleanup: Unsubscribe from the channel to save Redis memory
        if pubsub:
            await pubsub.unsubscribe(f"task_status_{task_id}")
            await pubsub.close()


def _deduct_credits(student_id_str: str, env_type: str, task_id: str, exec_time_ms: float):
    """Deduct compute credits from the student's tenant. 
    Formula: credits = (execution_time_ms / 1000) * pod_base_cost
    Runs synchronously after the WS loop completes.
    """
    try:
        db = SessionLocal()
        try:
            # Get student and tenant
            student = db.query(UserORM).filter(UserORM.id == student_id_str).first()
            if not student:
                return
            tenant = db.query(TenantORM).filter(TenantORM.id == student.tenant_id).first()
            if not tenant:
                return
            # Get pod base cost
            pod = db.query(PodCatalogORM).filter(PodCatalogORM.id == env_type).first()
            base_cost = pod.base_cost if pod else 1.0
            # Deduct: credits = (ms/1000) * base_cost, minimum 0.01
            credits_to_deduct = max(0.01, (exec_time_ms / 1000.0) * base_cost)
            tenant.compute_credits = max(0.0, tenant.compute_credits - credits_to_deduct)
            # Record transaction
            txn = BillingTransactionORM(
                id=uuid7(),
                tenant_id=tenant.id,
                student_id=student.id,
                task_id=task_id,
                pod_id=env_type,
                credits_deducted=credits_to_deduct,
                execution_time_ms=exec_time_ms
            )
            db.add(txn)
            db.commit()
            print(f"[BILLING] Deducted {credits_to_deduct:.4f} credits from {tenant.name}. Remaining: {tenant.compute_credits:.2f}")
        finally:
            db.close()
    except Exception as e:
        print(f"[BILLING ERROR] Failed to deduct credits: {e}")