import asyncio
import websockets
import json
import uuid

async def run_virtual_student():
    uri = "ws://127.0.0.1:8080/ws/execute"
    
    # The payload we are sending to the C++ Sandbox
    
    
    
    payloadCpp = {
        "student_id": str(uuid.uuid4()),
        "course_code": "MASTER-HACK-CPP-999",
        "language": "cpp",
        "stdin_data": "",
        "source_code": """#include <iostream>
#include <fstream>
#include <vector>
#include <unistd.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <sys/wait.h>
#include <signal.h> // 👈 NEW: Required for signal handling

using namespace std;

int main() {
    // 👈 NEW: Tell Linux NOT to instantly kill us if we exceed file size.
    // This allows out.write() to gracefully fail instead of crashing the app.
    signal(SIGXFSZ, SIG_IGN); 

    // 👈 NEW: Using 'endl' forces the buffer to flush to disk instantly
    cout << "🔥 INITIATING C++ MASTER RED-TEAM GAUNTLET 🔥" << endl << endl;

    // 1. PRIVILEGE DROP TEST
    cout << "[1] Testing Root Privileges..." << endl;
    uid_t uid = getuid();
    if (uid == 0) {
        cout << "    -> ❌ VULNERABLE: Running as ROOT!" << endl;
    } else {
        cout << "    -> ✅ SECURE: Running as restricted user (UID: " << uid << ")" << endl;
    }

    // 2. NETWORK ISOLATION TEST (Egress)
    cout << "\\n[2] Testing Network Isolation (Egress)..." << endl;
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        cout << "    -> ✅ SECURE: Socket creation blocked by Seccomp (EACCES)." << endl;
    } else {
        struct sockaddr_in server;
        server.sin_family = AF_INET;
        server.sin_port = htons(53);
        inet_pton(AF_INET, "8.8.8.8", &server.sin_addr);
        
        if (connect(sock, (struct sockaddr *)&server, sizeof(server)) < 0) {
            cout << "    -> ✅ SECURE: Network connection dropped/blocked." << endl;
        } else {
            cout << "    -> ❌ VULNERABLE: Network connection succeeded!" << endl;
        }
        close(sock);
    }

    // 3. DISK QUOTA TEST (Trying to write >1MB)
    cout << "\\n[3] Testing Disk Storage Limits (2MB Write)..." << endl;
    ofstream out("/tmp/bomb.txt", ios::binary);
    if (!out) {
        cout << "    -> ✅ SECURE: Cannot open file." << endl;
    } else {
        vector<char> buffer(1024 * 1024, '0'); // 1MB chunk
        out.write(buffer.data(), buffer.size());
        out.write(buffer.data(), buffer.size()); // Try to write 2nd MB
        
        if (out.bad() || out.fail()) {
            cout << "    -> ✅ SECURE: Disk limit enforced during write." << endl;
        } else {
            cout << "    -> ❌ VULNERABLE: Wrote 2MB file successfully!" << endl;
        }
        out.close();
    }

    // 4. FORK BOMB TEST (Process Limits)
    cout << "\\n[4] Testing Fork Bomb (Thread/Process Exhaustion)..." << endl;
    int processes = 0;
    for (int i = 0; i < 100; ++i) {
        pid_t pid = fork();
        if (pid == 0) { // Child
            sleep(1);
            exit(0);
        } else if (pid > 0) { // Parent
            processes++;
        } else {
            break; // Fork blocked
        }
    }
    // Clean up zombies
    for(int i = 0; i < processes; ++i) wait(NULL);
    
    if (processes < 100) {
        cout << "    -> ✅ SECURE: Fork limit enforced at " << processes << " processes." << endl;
    } else {
        cout << "    -> ❌ VULNERABLE: Created " << processes << " child processes!" << endl;
    }

    // 5. MEMORY BOMB TEST (>512MB RAM)
    cout << "\\n[5] Testing Memory Limits (Allocating 600MB)..." << endl;
    try {
        char* ptr = new char[600 * 1024 * 1024]; 
        
        // 👈 TUMI EI LOOP TA DITE VULE GESO!
        // Eita OS ke force korbe actual physical RAM use korte.
        // Protita 4KB page (Linux default) e ekta kore 'X' likhbe.
        for(int i = 0; i < 600 * 1024 * 1024; i += 4096) {
            ptr[i] = 'X'; 
        }
        
        cout << "    -> ❌ VULNERABLE: Memory allocation succeeded!" << endl;
        delete[] ptr;
    } catch (const std::bad_alloc& e) {
        cout << "    -> ✅ SECURE: Blocked by RAM limit (std::bad_alloc)." << endl;
    }

    // 6. INFINITE LOOP TEST (DoS / CPU Exhaustion)
    cout << "\\n[6] Testing CPU Timeout (5 Seconds)..." << endl;
    cout << "    -> Entering infinite loop. Wait 5 seconds for Mother Strategy hammer..." << endl;
    while (true) {
        // CPU gobbling loop
    }

    return 0;
}"""
    }

    payloadPython = {
        "student_id": str(uuid.uuid4()),
        "course_code": "MASTER-HACK-999",
        "language": "python",
        "stdin_data": "",
        "source_code": """import os, socket, time, sys

print("🔥 INITIATING MASTER RED-TEAM GAUNTLET 🔥\\n")

# 1. PRIVILEGE DROP TEST
print("[1] Testing Root Privileges...")
try:
    uid = os.getuid()
    if uid == 0:
        print("    -> ❌ VULNERABLE: Running as ROOT!")
    else:
        print(f"    -> ✅ SECURE: Running as restricted user (UID: {uid})")
except Exception as e:
    print(f"    -> Error: {e}")

# 2. NETWORK ISOLATION TEST (Egress)
print("\\n[2] Testing Network Isolation (Egress)...")
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    s.connect(("8.8.8.8", 53)) # Trying to reach Google DNS
    print("    -> ❌ VULNERABLE: Network connection succeeded!")
except Exception as e:
    print(f"    -> ✅ SECURE: Network blocked. ({e})")

# 3. DISK QUOTA TEST (Trying to write >1MB)
print("\\n[3] Testing Disk Storage Limits (2MB Write)...")
try:
    with open("/tmp/bomb.txt", "wb") as f:
        f.write(b"0" * 2 * 1024 * 1024) 
    print("    -> ❌ VULNERABLE: Wrote 2MB file successfully!")
except Exception as e:
    print(f"    -> ✅ SECURE: Disk limit enforced. ({e})")

# 4. FORK BOMB TEST (Process Limits)
print("\\n[4] Testing Fork Bomb (Thread/Process Exhaustion)...")
processes = 0
try:
    for _ in range(100):
        if os.fork() == 0:
            time.sleep(1)
            os._exit(0)
        processes += 1
    print(f"    -> ❌ VULNERABLE: Created {processes} child processes!")
except Exception as e:
    print(f"    -> ✅ SECURE: Fork limit enforced at {processes} processes. ({e})")

# 5. MEMORY BOMB TEST (>512MB RAM)
print("\\n[5] Testing Memory Limits (Allocating 600MB)...")
try:
    junk = bytearray(600 * 1024 * 1024)
    print("    -> ❌ VULNERABLE: Memory allocation succeeded!")
except MemoryError:
    print("    -> ✅ SECURE: Blocked by RAM limit (MemoryError).")
except Exception as e:
    print(f"    -> ✅ SECURE: Killed by OS. ({e})")

# 6. INFINITE LOOP TEST (DoS / CPU Exhaustion)
print("\\n[6] Testing CPU Timeout (5 Seconds)...")
print("    -> Entering infinite loop. Wait 5 seconds for Mother Strategy hammer...")
while True:
    pass
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