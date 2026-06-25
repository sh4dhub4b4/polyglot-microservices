import redis, json
r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
pods = {
    "cpp-basic": {"docker_image": "eci-cpp-engine:latest", "is_gui": False, "base_cost": 1.0},
    "python-ds": {"docker_image": "eci-python-engine:latest", "is_gui": False, "base_cost": 1.5},
    "java-basic": {"docker_image": "eci-jvm-engine:latest", "is_gui": False, "base_cost": 1.2},
    "csharp-dotnet": {"docker_image": "eci-dotnet-engine:latest", "is_gui": False, "base_cost": 1.2},
    "node-js": {"docker_image": "eci-node-engine:latest", "is_gui": False, "base_cost": 1.0},
    "go-sys": {"docker_image": "eci-go-engine:latest", "is_gui": False, "base_cost": 1.0},
    "rust-sys": {"docker_image": "eci-rust-engine:latest", "is_gui": False, "base_cost": 1.2},
    "gui-opengl": {"docker_image": "eci-gui-engine:latest", "is_gui": True, "base_cost": 3.0},
    "gui-java": {"docker_image": "eci-gui-engine:latest", "is_gui": True, "base_cost": 3.0},
    "wasm-cpp": {"docker_image": "eci-wasm-engine:latest", "is_gui": False, "base_cost": 1.0},
    "wasm-rust": {"docker_image": "eci-wasm-rust-engine:latest", "is_gui": False, "base_cost": 1.0},
    "wasm-go": {"docker_image": "eci-wasm-go-engine:latest", "is_gui": False, "base_cost": 1.0},
}
for pid, cfg in pods.items():
    r.set(f"pod_catalog:{pid}", json.dumps(cfg))
    print(f"[+] Synced {pid} to local Redis")

count = len(r.keys("pod_catalog:*"))
print(f"[*] Redis has {count} pod catalog entries")
