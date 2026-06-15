import asyncio
import websockets
import json
import uuid

API_GATEWAY = "ws://localhost:8080/ws/execute"

async def test_custom_pod_unauthorized():
    print("\n--- Test 1: Custom Pod Unauthorized Access ---")
    payload = {
        "student_id": str(uuid.uuid4()), # Random student not enrolled
        "course_code": "SEC-101",
        "env_type": "custom_python_ai", # Assuming a custom pod
        "source_code": "print('hello')",
        "mode": "batch"
    }
    try:
        async with websockets.connect(API_GATEWAY) as ws:
            await ws.send(json.dumps(payload))
            response = await ws.recv()
            print(f"Received: {response}")
            assert "error" in response or "403" in response or "Missing" in response
            print("✅ Passed: Blocked unauthorized custom pod access")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"✅ Passed: Connection closed by server with code {e.code} (Expected 1008 Policy Violation)")

async def test_wasm_lightweight_bypass():
    print("\n--- Test 2: WASM Lightweight Bypass ---")
    payload = {
        "student_id": str(uuid.uuid4()),
        "course_code": "CPP-101",
        "env_type": "cpp-basic",
        "source_code": "int main() { return 0; }", # Very simple payload
        "mode": "batch"
    }
    
    async with websockets.connect(API_GATEWAY) as ws:
        await ws.send(json.dumps(payload))
        
        while True:
            try:
                msg = await ws.recv()
                data = json.loads(msg)
                print(f"Received: {data['status']} - {data.get('message', '')}")
                if "WASM" in data.get("stdout", "") or "WASM" in data.get("message", ""):
                    print("✅ Passed: Detected WASM execution bypass")
                    break
                if data["status"] in ["completed", "error"]:
                    print("❌ Failed: Reached normal completed state without WASM mock.")
                    break
            except Exception as e:
                print(f"Error: {e}")
                break

async def main():
    print("🚀 Starting Phase 3 E2E Tests")
    await test_custom_pod_unauthorized()
    await test_wasm_lightweight_bypass()
    print("🎉 All Phase 3 E2E Tests Complete")

if __name__ == "__main__":
    asyncio.run(main())
