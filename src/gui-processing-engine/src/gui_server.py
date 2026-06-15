import os
import subprocess
import signal
import time
from typing import Dict, Optional
import asyncio
import json
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import threading

app = FastAPI(title="GUI Execution Node")

class ExecutionRequest(BaseModel):
    language: str
    source_code: str
    stdin_data: Optional[str] = ""

    class Config:
        extra = "ignore"

# State variables
current_process: Optional[subprocess.Popen] = None
last_activity_time: float = time.time()
IDLE_TIMEOUT_SECONDS = 600  # 10 minutes (Optimization Architect Guardrail)

def scale_to_zero_monitor():
    """Background thread that kills the pod if idle for > IDLE_TIMEOUT_SECONDS"""
    global last_activity_time
    while True:
        time.sleep(30)
        if time.time() - last_activity_time > IDLE_TIMEOUT_SECONDS:
            print("Idle timeout reached. Committing Seppuku to save RAM...", flush=True)
            # Exit process 0 to gracefully let K8s/Docker remove the pod
            os.kill(os.getpid(), signal.SIGTERM)

# Start scale-to-zero watcher
threading.Thread(target=scale_to_zero_monitor, daemon=True).start()

def kill_current_app():
    global current_process
    if current_process and current_process.poll() is None:
        try:
            current_process.terminate()
            current_process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            current_process.kill()
    current_process = None

@app.post("/api/v1/execute")
async def execute_gui_code(req: ExecutionRequest):
    global current_process, last_activity_time
    last_activity_time = time.time()
    
    # 1. Kill any existing running application (Hot-Reload)
    kill_current_app()

    # 2. Write files to isolated project directory
    project_dir = f"/tmp/gui_project"
    os.makedirs(project_dir, exist_ok=True)
    os.chown(project_dir, 10002, 10002) # Give ownership to sandboxuser
    
    main_file = os.path.join(project_dir, "main.cpp" if req.language == "gui-opengl" else "main.py" if req.language == "gui-python" else "Main.java")
    
    with open(main_file, "w") as f:
        f.write(req.source_code)
    os.chown(main_file, 10002, 10002) # Give ownership to sandboxuser

    if not main_file:
        raise HTTPException(status_code=400, detail="Could not determine main file")

    # 3. Compile and Run based on Language
    env = os.environ.copy()
    env["DISPLAY"] = ":99"
    
    try:
        if req.language == "gui-python":
            cmd = ["python3", main_file]
            
        elif req.language == "gui-java":
            # Compile Java as sandboxuser
            compile_cmd = ["javac", main_file]
            subprocess.run(compile_cmd, cwd=project_dir, check=True, user="sandboxuser", group="sandboxuser")
            # Run Java
            class_name = os.path.splitext(os.path.basename(main_file))[0]
            cmd = ["java", class_name]
            
        elif req.language == "gui-opengl":
            # Compile C++ OpenGL as sandboxuser
            compile_cmd = ["g++", main_file, "-o", "opengl_app", "-lGLEW", "-lglfw", "-lGL"]
            subprocess.run(compile_cmd, cwd=project_dir, check=True, user="sandboxuser", group="sandboxuser")
            cmd = ["./opengl_app"]
            
        else:
            raise HTTPException(status_code=400, detail="Unsupported GUI language")
            
        # Spawn the process asynchronously as an unprivileged user (sandboxuser)
        # This prevents attackers from escaping the sandbox or modifying the server
        current_process = subprocess.Popen(
            cmd,
            cwd=project_dir,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            user="sandboxuser",
            group="sandboxuser"
        )
        
        return {"status": "success", "message": f"App started on VNC Display :99"}
        
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=400, detail=f"Compilation Failed: {e}")

@app.websocket("/ws/execute")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    global current_process, last_activity_time
    last_activity_time = time.time()
    
    try:
        # 1. Receive JSON payload
        data = await websocket.receive_text()
        req_dict = json.loads(data)
        req = ExecutionRequest(**req_dict)
        
        # 2. Kill current app
        kill_current_app()
        
        # 3. Setup Project Dir
        project_dir = f"/tmp/gui_project"
        os.makedirs(project_dir, exist_ok=True)
        os.chown(project_dir, 10002, 10002)
        
        main_file = os.path.join(project_dir, "main.cpp" if req.language == "gui-opengl" else "main.py" if req.language == "gui-python" else "Main.java")
        with open(main_file, "w") as f:
            f.write(req.source_code)
        os.chown(main_file, 10002, 10002)
        
        # 4. Compile
        if req.language == "gui-python":
            cmd = ["python3", main_file]
        elif req.language == "gui-java":
            compile_cmd = ["javac", main_file]
            subprocess.run(compile_cmd, cwd=project_dir, check=True, user="sandboxuser", group="sandboxuser")
            class_name = os.path.splitext(os.path.basename(main_file))[0]
            cmd = ["java", class_name]
        elif req.language == "gui-opengl":
            compile_cmd = ["g++", main_file, "-o", "opengl_app", "-lGLEW", "-lglfw", "-lGL"]
            subprocess.run(compile_cmd, cwd=project_dir, check=True, user="sandboxuser", group="sandboxuser")
            cmd = ["./opengl_app"]
        else:
            await websocket.send_text(json.dumps({"status": "error", "message": "Unsupported GUI language"}))
            await websocket.close()
            return
            
        # 5. Run async process
        env = os.environ.copy()
        env["DISPLAY"] = ":99"
        
        def preexec():
            # change to sandboxuser
            os.setgid(10002)
            os.setuid(10002)
            
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=project_dir,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE,
            preexec_fn=preexec
        )
        
        # We don't store in global current_process because Popen and asyncio.Process are different
        # For hot-reload via POST, this might conflict, but for WS we manage it locally.
        
        # 6. Stream IO
        async def read_stream(stream, stream_type):
            while True:
                line = await stream.readline()
                if not line:
                    break
                await websocket.send_text(json.dumps({
                    "type": stream_type,
                    "data": line.decode('utf-8', errors='replace')
                }))
                
        async def write_stream(stream):
            try:
                while True:
                    data = await websocket.receive_text()
                    msg = json.loads(data)
                    if "stdin_data" in msg and msg["stdin_data"]:
                        stream.write(msg["stdin_data"].encode('utf-8'))
                        await stream.drain()
            except WebSocketDisconnect:
                pass
                
        stdout_task = asyncio.create_task(read_stream(process.stdout, "stdout"))
        stderr_task = asyncio.create_task(read_stream(process.stderr, "stderr"))
        stdin_task = asyncio.create_task(write_stream(process.stdin))
        
        start_time = time.time()
        await process.wait()
        end_time = time.time()
        
        stdout_task.cancel()
        stderr_task.cancel()
        stdin_task.cancel()
        
        await websocket.send_text(json.dumps({
            "status": "completed",
            "exit_code": process.returncode,
            "execution_time_ms": int((end_time - start_time) * 1000)
        }))
        
    except subprocess.CalledProcessError as e:
        await websocket.send_text(json.dumps({"status": "error", "message": f"Compilation Failed: {e}"}))
    except WebSocketDisconnect:
        print("WebSocket client disconnected")
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({"status": "error", "message": str(e)}))
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
