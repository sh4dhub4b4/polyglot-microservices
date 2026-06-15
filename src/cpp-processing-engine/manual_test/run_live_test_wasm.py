import subprocess
import time
import urllib.request
import json
import os

HOST_API_PORT = "8086" # Different port to avoid conflict with GUI engine

print("🚀 Step 1/4: Building C++ Docker Image with Emscripten (eci-native-engine)...")
subprocess.run(["docker", "build", "--target", "native-engine", "-t", "eci-native-engine", "-f", "src/cpp-processing-engine/Dockerfile.engine", "src/cpp-processing-engine"], check=True)

print("\n🚀 Step 2/4: Starting C++ Engine Container (test-wasm-pod)...")
subprocess.run(["docker", "rm", "-f", "test-wasm-pod"], capture_output=True)
subprocess.run(["docker", "run", "-d", "--name", "test-wasm-pod", "--privileged", "-p", f"{HOST_API_PORT}:8080", "eci-native-engine"], check=True)

print("\n⏳ Waiting for API Server to boot up (3 seconds)...")
time.sleep(3)

print("\n🚀 Step 3/4: Injecting C++ Code for WASM Compilation...")

# Simple C++ program to test WASM compilation
cpp_code = """
#include <iostream>
int main() {
    string x;
    std::cin>>x;
    std::cout << "🚀 Hello from WebAssembly! This C++ code was compiled by Emscripten in the Cloud!"<< x << std::endl;
    return 0;
}
"""

payload = {
    "project_id": "demo_wasm_001",
    "language": "wasm-cpp",
    "source_code": cpp_code
}

req = urllib.request.Request(
    f"http://localhost:{HOST_API_PORT}/api/v1/execute", 
    data=json.dumps(payload).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        print("\n✅ API Response Successfully Received!")
        
        # Save the resulting Javascript payload to an HTML file to test it locally in browser
        js_payload = result.get("stdout_output", "")
        if "Failed" in result.get("stderr_output", ""):
             print(f"❌ Compilation Failed: {result.get('stderr_output')}")
             exit(1)
             
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><title>WASM Test</title></head>
        <body style="background:#1e1e1e; color:#00ff00; font-family:monospace; padding: 20px;">
            <h2>ECI WebAssembly Execution Engine</h2>
            <div id="output"></div>
            <script>
                var Module = {{
                    print: function(text) {{
                        document.getElementById('output').innerHTML += text + '<br>';
                    }}
                }};
            </script>
            <script>
                // This is the raw Emscripten-compiled JS + Base64 WASM payload injected from the Cloud Engine
                {js_payload}
            </script>
        </body>
        </html>
        """
        
        test_file = "wasm_test_output.html"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        print(f"💾 Saved WASM Payload to {os.path.abspath(test_file)}")

except Exception as e:
    print(f"❌ API Failed: {e}")
    exit(1)

print("\n🎉 Step 4/4: Ready for Visual Inspection!")
print("=========================================================")
print(f"👉 OPEN {os.path.abspath('wasm_test_output.html')} IN YOUR BROWSER!")
print("=========================================================")
print("To stop the test and clean up, run: docker rm -f test-wasm-pod")
