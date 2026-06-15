import asyncio
import websockets
import json
import time
import re

# Mock Settings
WS_URL = "ws://127.0.0.1:8080/ws/execute"
COST_PER_CLOUD_EXECUTION = 0.005 # $0.005 per K8s execution
COST_PER_WASM_EXECUTION = 0.000  # $0.000 per WASM execution

# Test Matrix: Multi-layer Polyglot Students
STUDENTS = [
    {"uni": "BRACU", "dept": "CSE", "id": "ST_01", "lang": "cpp"},
    {"uni": "BRACU", "dept": "EEE", "id": "ST_02", "lang": "python"},
    {"uni": "NSU", "dept": "CSE", "id": "ST_03", "lang": "cpp"},
    {"uni": "NSU", "dept": "DATA", "id": "ST_04", "lang": "python"}
]

# Severity Levels
WORKLOADS = {
    "basic": {
        "cpp": "#include <iostream>\nint main() { std::cout << \"Basic Test Pass\"; return 0; }",
        "python": "print('Basic Test Pass')"
    },
    "mid": {
        "cpp": "#include <iostream>\nint main() { int sum = 0; for(int i=0; i<1000; i++) sum+=i; std::cout << sum; return 0; }",
        "python": "sum = 0\nfor i in range(1000): sum += i\nprint(sum)"
    },
    "hard": {
        # Infinite memory allocation
        "cpp": "#include <iostream>\nint main() { while(true) { new int[10000]; } return 0; }",
        "python": "arr = []\nwhile True: arr.append(' ' * 1000000)"
    },
    "adv": {
        # Trying to run bash or system commands (Malicious)
        "cpp": "#include <stdlib.h>\nint main() { system(\"ls -la /root\"); return 0; }",
        "python": "import os\nos.system('cat /etc/passwd')"
    }
}

class OptimizationRouter:
    """
    BUSINESS STANCE SUGGESTION: 
    This router inspects the code statically before deciding where to execute it.
    If it's safe and basic, it routes to WASM (saving $0.005 per run).
    If it contains dangerous/heavy operations, it routes to Cloud K8s to utilize the seccomp sandbox.
    """
    DANGEROUS_KEYWORDS = [r"system\(", r"exec\(", r"import os", r"subprocess", r"while\(true\)", r"while True"]
    
    @staticmethod
    def evaluate_route(code: str) -> str:
        for keyword in OptimizationRouter.DANGEROUS_KEYWORDS:
            if re.search(keyword, code):
                return "CLOUD_K8S" # Must go to the zero-trust sandbox
        
        # If it's a simple script, compile to WASM and run locally
        return "WASM_CLIENT"


async def mock_wasm_execution(student, severity, code):
    """Simulates 0-latency client-side WebAssembly execution."""
    start_time = time.time()
    await asyncio.sleep(0.01) # WASM is instantaneous
    exec_time = (time.time() - start_time) * 1000
    print(f"[WASM] {student['uni']}->{student['dept']}->{student['id']} | Sev: {severity} | Time: {exec_time:.1f}ms | Cost: $0.00")
    return {"status": "success", "cost": COST_PER_WASM_EXECUTION, "time": exec_time}

async def cloud_k8s_execution(student, severity, code, lang):
    """Connects to the actual backend API to execute in K8s Sandbox."""
    start_time = time.time()
    
    payload = {
        "student_id": f"{student['uni']}_{student['dept']}_{student['id']}",
        "language": lang,
        "source_code": code,
        "mode": "non-interactive"
    }
    
    try:
        async with websockets.connect(WS_URL) as ws:
            await ws.send(json.dumps(payload))
            
            output_log = ""
            while True:
                resp = await ws.recv()
                data = json.loads(resp)
                if 'stdout_output' in data:
                    output_log += data['stdout_output']
                if 'stderr_output' in data:
                    output_log += data['stderr_output']
                    
                if data.get('status') in ['completed', 'error']:
                    break
                    
        exec_time = (time.time() - start_time) * 1000
        
        # Check if malicious code was caught
        blocked = "false"
        if severity in ['hard', 'adv'] and ('Killed' in output_log or 'blocked' in output_log.lower() or data.get('exit_code', 0) != 0):
            blocked = "TRUE (Sandbox working)"
            
        print(f"[CLOUD] {student['uni']}->{student['dept']}->{student['id']} | Sev: {severity} | Time: {exec_time:.1f}ms | Cost: ${COST_PER_CLOUD_EXECUTION} | Blocked: {blocked}")
        return {"status": "success", "cost": COST_PER_CLOUD_EXECUTION, "time": exec_time}
        
    except Exception as e:
        print(f"[CLOUD ERROR] Gateway unreachable for {student['id']}: {str(e)}")
        return {"status": "error", "cost": 0, "time": 0}

async def run_student_workload(student, severity):
    code = WORKLOADS[severity][student["lang"]]
    
    # 1. Business Logic: Pass through Optimization Router
    route = OptimizationRouter.evaluate_route(code)
    
    # 2. Execute based on Route
    if route == "WASM_CLIENT":
        return await mock_wasm_execution(student, severity, code)
    else:
        return await cloud_k8s_execution(student, severity, code, student["lang"])

async def main():
    print("="*60)
    print("POLYGLOT HYBRID ROUTING BENCHMARK TEST")
    print("Testing WASM Cost-Saving vs Cloud Security Isolation")
    print("="*60)
    
    tasks = []
    total_cost_without_router = 0.0
    
    for severity in ["basic", "mid", "hard", "adv"]:
        for student in STUDENTS:
            tasks.append(run_student_workload(student, severity))
            total_cost_without_router += COST_PER_CLOUD_EXECUTION
            
    print("Deploying workloads concurrently...\n")
    results = await asyncio.gather(*tasks)
    
    actual_cost = sum(r["cost"] for r in results if r["status"] == "success")
    savings = total_cost_without_router - actual_cost
    
    print("\n" + "="*60)
    print("BUSINESS IMPACT REPORT")
    print("="*60)
    print(f"Total Executions: {len(tasks)}")
    print(f"Projected Cost (100% Cloud): ${total_cost_without_router:.4f}")
    print(f"Actual Cost (Hybrid WASM Router): ${actual_cost:.4f}")
    print(f"Total Money Saved: ${savings:.4f} ({(savings/total_cost_without_router)*100:.1f}%)")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
