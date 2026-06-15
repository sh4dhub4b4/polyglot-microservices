import re

def is_lightweight_payload(source_code: str, env_type: str) -> bool:
    """
    Detects if the source code is simple enough to be run via WASM,
    bypassing heavy K8s pod creation to save cloud OpEx.
    """
    if not source_code or not env_type:
        return False
        
    env_lower = env_type.lower()
    
    # 1. We only support certain languages for WASM offloading right now
    if env_lower not in ["cpp-basic", "c-basic", "rust-sys"]:
        return False

    # 2. Check for heavy imports or system calls
    # For C/C++
    if env_lower in ["cpp-basic", "c-basic"]:
        heavy_includes = ["<thread>", "<mutex>", "<sys/socket.h>", "<pthread.h>", "<unistd.h>"]
        if any(heavy in source_code for heavy in heavy_includes):
            return False
            
    # For Rust
    if env_lower == "rust-sys":
        heavy_crates = ["std::thread", "std::net", "tokio", "async"]
        if any(heavy in source_code for heavy in heavy_crates):
            return False

    # 3. Check for arbitrary code execution patterns or file system access
    suspicious_patterns = [
        r"system\(", 
        r"exec\(", 
        r"popen\(", 
        r"fork\(",
        r"fopen\(",
        r"std::ofstream",
        r"std::ifstream"
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, source_code):
            return False
            
    # 4. Length check (very long files might need a real pod for dependencies)
    if len(source_code) > 5000:
        return False

    # If it passes all checks, it's lightweight enough for WASM!
    return True
