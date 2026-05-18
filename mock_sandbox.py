from fastapi import FastAPI
from pydantic import BaseModel
import sys
import io
import contextlib
import uvicorn

app = FastAPI()

class ExecuteRequest(BaseModel):
    language: str
    source_code: str

@app.post("/api/v1/execute")
def execute_code(req: ExecuteRequest):
    print(f"\n[SANDBOX] Received {req.language} code payload. Executing...")
    stdout = io.StringIO()
    stderr = io.StringIO()
    
    # Capture the output of the student's code
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            exec(req.source_code)
            exit_code = 0
        except Exception as e:
            print(e, file=sys.stderr)
            exit_code = 1
            
    print("[SANDBOX] Execution complete. Returning results to API Gateway.")
    
    return {
        "exit_code": exit_code,
        "stdout_output": stdout.getvalue(),
        "stderr_output": stderr.getvalue(),
        "memory_limit_exceeded": False
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)