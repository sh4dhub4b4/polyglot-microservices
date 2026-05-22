import asyncio
import websockets
import json
import uuid
import time
import random

# 🌍 THE I/O STRESS PAYLOADS (Testing the RAM Disk)
PAYLOADS = {
    "cpp": {
        "language": "cpp",
        "course_code": "CS-201-ADV-CPP",
        "source_code": r"""#include <iostream>
using namespace std;
int main(){
string x;
cin>>x;
cout<<"Hello "<<x<<endl;
return 0;}"""
    },
    "python": {
        "language": "python",
        "course_code": "DS-301-PYTHON",
        "source_code": r"""
x=input();print("Hello ",x)
"""  # Intentional Syntax Error (printf instead of print)
    },
    "go": {
        "language": "go",
        "course_code": "DS-308-GO",
        "source_code": r"""package main

import "fmt"

func main() {
    var name string
    var age int
    
    fmt.Println("Enter name and age:")
    fmt.Scanln(&name, &age)  // Reads until newline
    
    fmt.Printf("Hello %s, you are %d years old  %s", name, age)
}"""},
    "c": {
        "language": "c",
        "course_code": "DS-308-C",
        "source_code": r"""#include<stdio.h>
int main(){
printf("I'm in C.\n");
return 0;}
""",
    
    },

    "javascript": {
        "language": "javascript",
        "course_code": "WEB-101-JS",
        "source_code": r"""const fs = require('fs');

// Read all of stdin directly from file descriptor 0 (Standard for CP platforms)
const input = fs.readFileSync(0, 'utf-8').trim();

console.log(`Hello ${input} from Node.js!`);"""
    },
    
    "rust": {
        "language": "rust",
        "course_code": "SYS-402-RUST",
        "source_code": r"""use std::io::{self, Write};

fn main() {
    println!("Enter your name:");
    
    let mut name = String::new();
    io::stdin()
        .read_line(&mut name)
        .expect("Failed to read line");
    
    let name = name.trim();
    println!("Hello {} from Rust! 🦀", name);
}"""
    }

}


async def run_virtual_student(student_number):
    uri = "ws://127.0.0.1:8080/ws/execute"
    await asyncio.sleep(random.uniform(0.0, 1.0)) # Anti-DDoS Jitter
    
    stdId = str(uuid.uuid4())

    lang = ["rust","javascript","cpp","c","go","python"]  # Test all three
    for lang_choice in lang:
        payload = {
        "student_id": stdId,
        "course_code": PAYLOADS[lang_choice]["course_code"],
        "language": PAYLOADS[lang_choice]["language"],
        "stdin_data": r"""kokil 90
""",
        "source_code": PAYLOADS[lang_choice]["source_code"]
        }
        
        try:
            async with websockets.connect(uri) as websocket:
                await websocket.send(json.dumps(payload))
                while True:
                    response = await websocket.recv()
                    data = json.loads(response)
                    # print(data)
                    status = data.get("status")
                    
                    if status == "executing":
                        print(f"🚀 [Std-{student_number:02d} | {lang_choice.upper()}] EXECUTING CODE...")
                    elif status == "completed":
                        print(f"✅ [Std-{student_number:02d} | {lang_choice.upper()}] EXECUTION COMPLETED")
                        print(f"   ┣ Exit Code: {data.get('exit_code')}")
                        
                        # Handle Explicit Compilation Failures
                        if data.get("compilation_failed"):
                            print(f"   ┣ 🚨 COMPILATION ERROR:\n{data.get('stderr_output', '').strip()}")
                        else:
                            # Handle Runtime Outputs (Both Stderr and Stdout)
                            stdout = data.get('stdout_output', '').strip()
                            stderr = data.get('stderr_output', '').strip()
                            
                            if stdout:
                                print(f"   ┣ 📝 STDOUT:\n{stdout}")
                            if stderr:
                                print(f"   ┣ ⚠️ STDERR (Runtime Error):\n{stderr}")
                                
                        print("-" * 60)
                        break
                    elif status == "error":
                        print(f"❌ [Std-{student_number:02d}] SYSTEM ERROR: {data['message']}")
                        break
        except Exception as e:
            print(f"❌ [Std-{student_number:02d}] Connection failed: {e}")

async def main():
    print("🌐 LAUNCHING RAM-DISK & PARALLEL OPTIMIZATION VALIDATION 🌐")
    print("Sending 1 concurrent I/O intensive workloads to K8s Sandbox...\n")
    tasks = [run_virtual_student(1)]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())