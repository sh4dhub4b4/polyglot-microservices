import asyncio
import websockets
import json
import uuid

async def run_virtual_student():
    uri = "ws://127.0.0.1:8080/ws/execute"
    
    # The payload we are sending to the C++ Sandbox
    
    
    
    payloadCpp = {
        "student_id": str(uuid.uuid4()),
        "course_code": "CSE-102-CPP",
        "language": "cpp", # 👈 'cpp' language!
        "stdin_data": "150", 
        "source_code": """#include <bits/stdc++.h>
using namespace std;

int main() {
    int x;
    cin >> x;
    cout << "🚀 C++ Sandbox Engine is Live!" << endl;
    cout << "Data received: " << x << endl;
    cout << "Processed Value: " << (x * 2) << endl;
    return 0;
}"""
    }
    payloadPython = {
        "student_id": str(uuid.uuid4()),
        "course_code": "CSE-101-Python",
        "language": "python",
        "stdin_data": "150",
        "source_code": """x=input()
print(x)
"""
    }
    payloadC = {
        "student_id": str(uuid.uuid4()),
        "course_code": "CSE-103-C",
        "language": "c",
        "stdin_data": "150",
        "source_code": """#include<stdio.h>
int main(){
int num;
scanf("%d",%num);
printf("Ami jei number paisi %d\n",num);
return 0;
}
"""
    }
    payload=payloadCpp # <= ei line modify kore lang change korbo

    print("🔌 Connecting to ECI WebSocket API...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected! Sending code payload...\n")
            await websocket.send(json.dumps(payload))
            
            # Listen to the live stream
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                print(f'server(execution_ws.py) -> client(test_e2e_gauntlet.py) : {data}')
                
                status = data.get("status")
                
                if status == "provisioning":
                    print(f"⏳ ORCHESTRATOR: {data['message']}")
                elif status == "executing":
                    print(f"🚀 SANDBOX: {data['message']}\n")
                    print("-" * 40)
                elif status == "completed":
                    print(data.get("stdout_output", ""))
                    if data.get("stderr_output"):
                        print(f"⚠️ ERRORS:\n{data.get('stderr_output')}")
                    print("-" * 40)
                    print(f"✅ FINISHED with Exit Code: {data.get('exit_code')}")
                    break
                elif status == "error":
                    print(f"❌ CRITICAL ERROR: {data['message']}")
                    break
                    
    except ConnectionRefusedError:
        print("❌ Could not connect. Is the API Gateway running on port 8000?")

if __name__ == "__main__":
    asyncio.run(run_virtual_student())