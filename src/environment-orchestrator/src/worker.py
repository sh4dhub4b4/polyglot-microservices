import os
import json
import time
import redis
from k8s_manager import K8sEnvironmentManager

# SRE Note: Worker will use synchronous Redis to match k8s_manager's synchronous flow
REDIS_HOST = os.getenv("REDIS_HOST", "redis-svc.eci-system.svc.cluster.local")
redis_client = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)

k8s_manager = K8sEnvironmentManager()

def publish_status(task_id: str, status: str, message: str, extra: dict = None):
    """Helper function to broadcast messages back to the API Gateway via Pub/Sub"""
    payload = {"status": status, "message": message}
    if extra:
        payload.update(extra)
    redis_client.publish(f"task_status_{task_id}", json.dumps(payload))

def run_worker():
    print("👷 Orchestrator Worker started. Listening for tasks on 'execution_queue'...")
    
    while True:
        try:
            # blpop blocks the loop safely until a new task arrives (Zero CPU waste!)
            result = redis_client.blpop("execution_queue", timeout=0)
            if not result:
                continue
            
            _, task_data = result
            task = json.loads(task_data)
            task_id = task.get("task_id")
            
            if not task_id:
                continue
                
            print(f"📥 Received execution task: {task_id}")
            
            # Phase 1: Provisioning
            publish_status(task_id, "provisioning", "Allocating secure K8s cluster resources...")
            prov_res = k8s_manager.provision_sandbox(
                student_id=task["student_id"],
                course_code=task["course_code"],
                env_type=task["language"]
            )
            pod_name = prov_res.get("pod_name")
            
            # Phase 2: Execution
            publish_status(task_id, "executing", f"Sandbox [{pod_name}] is ready! Injecting payload...")
            
            # Note: execute_code dynamically routes to the pod and fetches stdout/stderr
            exec_res = k8s_manager.execute_code(
                pod_name=pod_name,
                source_code=task["source_code"],
                stdin_data=task.get("stdin_data", ""),
                env_type=task["language"]
            )
            
            # Phase 3: Completed
            publish_status(task_id, "completed", "Execution finished successfully", extra=exec_res)
            
        except Exception as e:
            print(f"❌ Error processing task: {str(e)}")
            if 'task_id' in locals() and task_id:
                publish_status(task_id, "error", f"Worker Execution Error: {str(e)}")
            time.sleep(2) # Cooldown in case of repeated rapid failures

if __name__ == "__main__":
    run_worker()