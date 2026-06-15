import subprocess
import time
import urllib.request
import json
import webbrowser

HOST_API_PORT = "8085"
HOST_VNC_PORT = "5905"

print("🚀 Step 1/4: Building GUI Docker Image (eci-gui-engine)...")
subprocess.run(["docker", "build", "-t", "eci-gui-engine", "-f", "src/gui-processing-engine/Dockerfile.gui", "src/gui-processing-engine"], check=True)

print("\n🚀 Step 2/4: Starting GUI Container (test-gui-pod)...")
# Cleanup any existing
subprocess.run(["docker", "rm", "-f", "test-gui-pod"], capture_output=True)
# Run new
subprocess.run(["docker", "run", "-d", "--name", "test-gui-pod", "-p", f"{HOST_API_PORT}:8080", "-p", f"{HOST_VNC_PORT}:6080", "eci-gui-engine"], check=True)

print("\n⏳ Waiting for Xvfb and VNC server to boot up (5 seconds)...")
time.sleep(5)

print("\n🚀 Step 3/4: Injecting Python Tkinter Code via API...")

# A cool Tkinter digital clock as a test payload
tk_code = """
import tkinter as tk
import time

def tick():
    time_string = time.strftime("%H:%M:%S")
    clock.config(text=time_string)
    clock.after(200, tick)

root = tk.Tk()
root.title("Polyglot GUI Sandbox - Live Demo")
root.geometry("400x200")
root.configure(bg="black")

label = tk.Label(root, text="Welcome to Cloud VNC!", font=("Helvetica", 14), bg="black", fg="green")
label.pack(pady=20)

clock = tk.Label(root, font=("Courier", 40, "bold"), bg="black", fg="cyan")
clock.pack()

tick()
root.mainloop()
"""

payload = {
    "project_id": "demo_live_001",
    "language": "python-tk",
    "files": {
        "main.py": tk_code
    }
}

req = urllib.request.Request(
    f"http://localhost:{HOST_API_PORT}/execute", 
    data=json.dumps(payload).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        print(f"✅ API Response: {result}")
except Exception as e:
    print(f"❌ API Failed: {e}")
    exit(1)

print("\n🎉 Step 4/4: Ready for Visual Inspection!")
vnc_url = f"http://localhost:{HOST_VNC_PORT}/vnc_lite.html"
print("=========================================================")
print(f"👉 CLICK HERE TO VIEW YOUR GUI: {vnc_url}")
print("=========================================================")
print("When you open the link, click the 'Connect' button.")
print("To stop the test and clean up, run: docker rm -f test-gui-pod")

try:
    webbrowser.open(vnc_url)
except:
    pass

