import subprocess
import time
import urllib.request
import json

HOST_API_PORT = "8085"

print("Step 1/4: Building GUI Docker Image with OpenGL Support (eci-gui-engine)...")
subprocess.run(["docker", "build", "-t", "eci-gui-engine", "-f", "src/gui-processing-engine/Dockerfile.gui", "src/gui-processing-engine"], check=True)

print("\nStep 2/4: Starting GUI Container (test-gui-pod)...")
# Cleanup first
subprocess.run(["docker", "rm", "-f", "test-gui-pod"], capture_output=True)
# Run container mapping ports
subprocess.run([
    "docker", "run", "-d", 
    "--name", "test-gui-pod", 
    "-p", f"{HOST_API_PORT}:8080", 
    "-p", "5905:6080", 
    "eci-gui-engine"
], check=True)

print("\nWaiting for Xvfb and VNC server with OpenGL extension to boot up (5 seconds)...")
time.sleep(5)

print("\nStep 3/4: Injecting OpenGL glxgears via Python script...")

# This python script launches the systems GLX gears application to render 3D rotating gears.
opengl_python_code = """
import subprocess
import time
import sys

print("Spawning glxgears to render 3D gears via Software OpenGL...", flush=True)

# Run glxgears and print its output (it will show FPS in stdout/stderr)
process = subprocess.Popen(["glxgears", "-info"], stdout=sys.stdout, stderr=sys.stderr)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    process.terminate()
"""

payload = {
    "project_id": "demo_opengl_gears",
    "language": "python-tk", # Run it as python
    "files": {
        "main.py": opengl_python_code
    }
}

req = urllib.request.Request(
    f"http://localhost:{HOST_API_PORT}/execute", 
    data=json.dumps(payload).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req) as response:
        print(f"API Response: {json.loads(response.read().decode('utf-8'))}")
except Exception as e:
    print(f"API Injection Failed: {e}")
    exit(1)

print("\nStep 4/4: Ready for Visual Inspection!")
print("=========================================================")
print("CLICK HERE TO VIEW SPARKING OPENGL GEARS: http://localhost:5905/vnc_lite.html")
print("=========================================================")
print("When you open the link, click the 'Connect' button.")
print("To stop the test and clean up, run: docker rm -f test-gui-pod")
