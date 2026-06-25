import os
import sys
import uuid
import json
import subprocess
# Add src/api-gateway to path so we can import its modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'api-gateway', 'src'))

from infrastructure.database import SessionLocal, engine, Base
from sqlalchemy_utils import Ltree
import infrastructure.orm_models as models

def seed_db():
    print("Ensuring tables are created...")
    
    # ALWAYS clean the DB before seeding to ensure a clean slate
    if os.path.exists("platform_dev.db"):
        try:
            os.remove("platform_dev.db")
        except PermissionError:
            pass
            
    if os.path.exists("src/api-gateway/platform_dev.db"):
        try:
            os.remove("src/api-gateway/platform_dev.db")
        except PermissionError:
            print("⚠️ Database file locked (Dev Mode). Dropping tables instead...")
            Base.metadata.drop_all(bind=engine)
            
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        print("Seeding Pod Catalog...")
        
        # Define all our newly built language pods
        pods = [
            models.PodCatalogORM(id="cpp-basic", name="C++ Sandbox", docker_image="eci-cpp-engine:latest", language="cpp", is_gui=False, base_cost=1.0),
            models.PodCatalogORM(id="python-ds", name="Python Data Science", docker_image="eci-python-engine:latest", language="python", is_gui=False, base_cost=1.5),
            models.PodCatalogORM(id="java-basic", name="Java 21 JVM", docker_image="eci-jvm-engine:latest", language="jvm", is_gui=False, base_cost=1.2),
            models.PodCatalogORM(id="csharp-dotnet", name="C# .NET 8.0", docker_image="eci-dotnet-engine:latest", language="dotnet", is_gui=False, base_cost=1.2),
            models.PodCatalogORM(id="node-js", name="Node.js Engine", docker_image="eci-node-engine:latest", language="javascript", is_gui=False, base_cost=1.0),
            models.PodCatalogORM(id="go-sys", name="Go 1.22", docker_image="eci-go-engine:latest", language="go", is_gui=False, base_cost=1.0),
            models.PodCatalogORM(id="rust-sys", name="Rust Cargo", docker_image="eci-rust-engine:latest", language="rust", is_gui=False, base_cost=1.2),
            models.PodCatalogORM(id="gui-opengl", name="OpenGL GUI", docker_image="eci-gui-engine:latest", language="cpp", is_gui=True, base_cost=3.0),
            models.PodCatalogORM(id="gui-java", name="Java Swing GUI", docker_image="eci-gui-engine:latest", language="jvm", is_gui=True, base_cost=3.0),
            models.PodCatalogORM(id="wasm-cpp", name="C++ WASM", docker_image="eci-wasm-engine:latest", language="cpp", is_gui=False, base_cost=1.0),
            models.PodCatalogORM(id="wasm-rust", name="Rust WASM", docker_image="eci-wasm-rust-engine:latest", language="rust", is_gui=False, base_cost=1.0),
            models.PodCatalogORM(id="wasm-go", name="Go WASM", docker_image="eci-wasm-go-engine:latest", language="go", is_gui=False, base_cost=1.0),
        ]
        
        for pod in pods:
            existing = db.query(models.PodCatalogORM).filter(models.PodCatalogORM.id == pod.id).first()
            if not existing:
                db.add(pod)
                print(f"[+] Added {pod.id} to Catalog.")
            else:
                # Update existing records to reflect script changes
                existing.name = pod.name
                existing.docker_image = pod.docker_image
                existing.is_gui = pod.is_gui
                existing.base_cost = pod.base_cost
                print(f"[*] Updated {pod.id} in Catalog.")
                
        db.commit()
        print("[*] Committed PodCatalog updates.")

        # Redis Sync via kubectl (Phase 1.2: Orchestrator Cache)
        print("[*] Synchronizing PodCatalog to K8s Redis via kubectl...")
        for pod in pods:
            json_val = json.dumps({
                "docker_image": pod.docker_image,
                "is_gui": pod.is_gui,
                "base_cost": pod.base_cost
            })
            # Use kubectl to set the key directly inside the cluster
            cmd = [
                "kubectl", "exec", "deployment/redis", "-n", "eci-system", "--",
                "redis-cli", "set", f"pod_catalog:{pod.id}", json_val
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                print(f"[!] Warning: Failed to sync {pod.id} to Redis. {e.stderr.decode('utf-8') if e.stderr else ''}")
        print("[*] Synchronized PodCatalog to Redis cache.")

        # Seed a dummy tenant (University) and map all pods to them so testing works smoothly
        dummy_tenant_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        dummy_tenant = db.query(models.TenantORM).filter(models.TenantORM.id == dummy_tenant_id).first()
        if not dummy_tenant:
            dummy_tenant = models.TenantORM(
                id=dummy_tenant_id,
                name="University",
                type=models.TenantType.UNIVERSITY,
                path=Ltree("university"),
                compute_credits=10000.0,
                subscription_tier="Enterprise"
            )
            db.add(dummy_tenant)
            db.commit()
            print(f"[+] Created dummy tenant '{dummy_tenant.name}'.")

        print("\nMapping pods to Dummy Tenant (University)...")
        for pod in pods:
            existing_map = db.query(models.TenantEnabledPodsORM).filter(
                models.TenantEnabledPodsORM.tenant_path == dummy_tenant.path,
                models.TenantEnabledPodsORM.pod_id == pod.id
            ).first()
            if not existing_map:
                db.add(models.TenantEnabledPodsORM(tenant_path=dummy_tenant.path, pod_id=pod.id))
                print(f"[-] Mapped {pod.id} to dummy tenant.")

        db.commit()
        print("\n[*] DB Seeding Complete.")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        db.rollback()
        print(f"[!] Error during seeding: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
