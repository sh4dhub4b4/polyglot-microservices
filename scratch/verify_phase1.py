import asyncio
import websockets
import json
import uuid

async def verify_phase1():
    uri = "ws://127.0.0.1:8080/ws/execute"
    payload = {
        "mode": "batch",
        "student_id": str(uuid.uuid4()),
        "course_code": "PHASE1-TEST",
        "env_type": "cpp-basic",
        "source_code": "#include <iostream>\nint main() { std::cout << \"Phase 1 Decoupling Success!\" << std::endl; return 0; }",
        "is_gui": False
    }

    try:
        async with websockets.connect(uri) as websocket:
            print("[Gateway] Connected!")
            await websocket.send(json.dumps(payload))
            print("[Gateway] Payload sent successfully!")
            
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                print(f"[Orchestrator] Status: {data.get('status')} - {data.get('message')}")
                
                if data.get("status") == "completed":
                    print("\n[SUCCESS] TEST PASSED: The Orchestrator successfully provisioned the pod using Redis routing!")
                    if "output" in data.get("extra", {}):
                        print(f"Code Output: {data['extra']['output']}")
                    break
                elif data.get("status") == "error":
                    print(f"\n[FAILED] TEST FAILED: {data.get('message')}")
                    break
    except Exception as e:
        print(f"[!] Error: {e}")

if __name__ == "__main__":
    asyncio.run(verify_phase1())
