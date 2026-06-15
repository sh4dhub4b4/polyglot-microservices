# ============================================================
# Hybrid Smart Makefile
# Industry-Grade TAG Strategy:
#   LOCAL  -> timestamp saved to .build_tag file (build & deploy decoupledd)
#   CLOUD  -> Git SHA (immutable, traceable, reproducible)
# ============================================================
TAG_FILE    := .build_tag
LOCAL_TAG   := $(shell cat $(TAG_FILE) 2>/dev/null || echo "none")
CLOUD_TAG   := $(shell git rev-parse HEAD 2>/dev/null || echo "dev")

# ⚠️ TUMI EKHAANE TOMAR GITHUB USERNAME DEBE (lowercase)
GITHUB_USER := sh4dhub4b4
REGISTRY    := ghcr.io/$(GITHUB_USER)/polyglot-microservices

.PHONY: init build-local build-python build-native build-jvm build-dotnet build-orch build-gw clean deploy-local deploy-cloud all all-local tst

init:
	@echo "🛠️ Checking and Initializing Kubernetes Namespaces..."
	@kubectl create namespace eci-system --dry-run=client -o yaml | kubectl apply -f -
	@kubectl create namespace eci-sandboxes --dry-run=client -o yaml | kubectl apply -f -
	@if [ -d "k8s" ]; then kubectl apply -f k8s/; fi

# --- Individual Build Targets (called with TAG from build-local, NOT standalone) ---
build-base:
	docker build -t polyglot-base-pod:latest -f docker/base/base-pod.Dockerfile .

build-python: build-base
	docker build -t eci-python-engine:v$(TAG) -f docker/runtime/python-pod.Dockerfile .

build-native: build-base
	docker build -t eci-cpp-engine:v$(TAG) -f docker/runtime/cpp-pod.Dockerfile .

build-jvm: build-base
	docker build -t eci-jvm-engine:v$(TAG) -f docker/runtime/java-pod.Dockerfile .

build-dotnet: build-base
	docker build -t eci-dotnet-engine:v$(TAG) -f docker/runtime/csharp-pod.Dockerfile .

build-go: build-base
	docker build -t eci-go-engine:v$(TAG) -f docker/runtime/go-pod.Dockerfile .

build-rust: build-base
	docker build -t eci-rust-engine:v$(TAG) -f docker/runtime/rust-pod.Dockerfile .

build-node: build-base
	docker build -t eci-node-engine:v$(TAG) -f docker/runtime/node-pod.Dockerfile .

build-wasm: build-base
	docker build -t eci-wasm-engine:v$(TAG) -f docker/runtime/wasm-pod.Dockerfile .

build-gui:
	docker build -t eci-gui-engine:v$(TAG) -f src/gui-processing-engine/Dockerfile.gui src/gui-processing-engine/

build-orch:
	docker build -t eci-orchestrator:v$(TAG) -f src/environment-orchestrator/Dockerfile src/environment-orchestrator/

build-gw:
	docker build -t eci-gateway:v$(TAG) -f src/api-gateway/Dockerfile src/api-gateway/

# --- Main Local Build: Freezes TAG at build time, saves to .build_tag ---
# deploy-local will READ from .build_tag, guaranteeing the same tag always.
build-local:
	$(eval BUILD_TAG := $(shell date +%s))
	@echo "📦 [LOCAL] Building images in batches to prevent IO thrashing | TAG=v$(BUILD_TAG)"
	export DOCKER_BUILDKIT=1 && $(MAKE) build-base
	export DOCKER_BUILDKIT=1 && $(MAKE) -j 3 build-python build-native build-jvm build-dotnet TAG=$(BUILD_TAG)
	export DOCKER_BUILDKIT=1 && $(MAKE) -j 3 build-go build-rust build-node build-wasm build-gui TAG=$(BUILD_TAG)
	export DOCKER_BUILDKIT=1 && $(MAKE) -j 2 build-orch build-gw TAG=$(BUILD_TAG)
	@echo $(BUILD_TAG) > $(TAG_FILE)
	@echo "✅ Build complete! TAG=v$(BUILD_TAG) saved to $(TAG_FILE)."
	@echo "👉 Run 'make clean deploy-local' to deploy."

clean:
	@echo "🧹 Cleaning old sandboxes..."
	-@kubectl delete pods --all -n eci-sandboxes --ignore-not-found=true --grace-period=0 --force 2>/dev/null || true

deploy-local: init
	$(eval DEPLOY_TAG := $(shell cat $(TAG_FILE) 2>/dev/null || echo ""))
	@if [ -z "$(DEPLOY_TAG)" ]; then \
		echo "❌ ERROR: No build tag found. Run 'make build-local' first!"; exit 1; \
	fi
	@echo "🔄 [LOCAL] Deploying with TAG from $(TAG_FILE): v$(DEPLOY_TAG)"
	kubectl set image deployment/eci-gateway gateway=eci-gateway:v$(DEPLOY_TAG) -n eci-system
	kubectl set image deployment/eci-orchestrator orchestrator=eci-orchestrator:v$(DEPLOY_TAG) -n eci-system
	kubectl set env deployment/eci-orchestrator CPP_ENGINE_TAG=v$(DEPLOY_TAG) IMAGE_REGISTRY="" -n eci-system
	kubectl rollout status deployment/eci-gateway -n eci-system
	kubectl rollout status deployment/eci-orchestrator -n eci-system
	@echo "🔄 [LOCAL] Updating sandbox engine images..."
	kubectl set image daemonset/sandbox-image-prepuller cpp-prepuller=eci-cpp-engine:v$(DEPLOY_TAG) -n eci-sandboxes
	kubectl set image daemonset/sandbox-image-prepuller python-prepuller=eci-python-engine:v$(DEPLOY_TAG) -n eci-sandboxes
	kubectl set image deployment/prewarmed-cpp-engine secure-engine=eci-cpp-engine:v$(DEPLOY_TAG) -n eci-sandboxes
	kubectl set image deployment/prewarmed-python-engine secure-engine=eci-python-engine:v$(DEPLOY_TAG) -n eci-sandboxes
	kubectl set image deployment/prewarmed-jvm-engine secure-engine=eci-jvm-engine:v$(DEPLOY_TAG) -n eci-sandboxes
	kubectl set image deployment/prewarmed-dotnet-engine secure-engine=eci-dotnet-engine:v$(DEPLOY_TAG) -n eci-sandboxes
	kubectl set image deployment/prewarmed-go-engine secure-engine=eci-go-engine:v$(DEPLOY_TAG) -n eci-sandboxes
	kubectl set image deployment/prewarmed-rust-engine secure-engine=eci-rust-engine:v$(DEPLOY_TAG) -n eci-sandboxes
	kubectl set image deployment/prewarmed-node-engine secure-engine=eci-node-engine:v$(DEPLOY_TAG) -n eci-sandboxes
	kubectl set image deployment/prewarmed-wasm-engine secure-engine=eci-wasm-engine:v$(DEPLOY_TAG) -n eci-sandboxes
	kubectl set image deployment/prewarmed-wasm-rust-engine secure-engine=eci-rust-engine:v$(DEPLOY_TAG) -n eci-sandboxes
	kubectl set image deployment/prewarmed-wasm-go-engine secure-engine=eci-go-engine:v$(DEPLOY_TAG) -n eci-sandboxes
	kubectl set image deployment/gui-engine gui-engine=eci-gui-engine:v$(DEPLOY_TAG) -n eci-sandboxes
	kubectl rollout status deployment/prewarmed-cpp-engine -n eci-sandboxes
	kubectl rollout status deployment/prewarmed-python-engine -n eci-sandboxes
	kubectl rollout status deployment/prewarmed-jvm-engine -n eci-sandboxes
	kubectl rollout status deployment/prewarmed-dotnet-engine -n eci-sandboxes
	kubectl rollout status deployment/prewarmed-go-engine -n eci-sandboxes
	kubectl rollout status deployment/prewarmed-rust-engine -n eci-sandboxes
	kubectl rollout status deployment/prewarmed-node-engine -n eci-sandboxes
	kubectl rollout status deployment/prewarmed-wasm-engine -n eci-sandboxes
	kubectl rollout status deployment/prewarmed-wasm-rust-engine -n eci-sandboxes
	kubectl rollout status deployment/prewarmed-wasm-go-engine -n eci-sandboxes
	kubectl rollout status deployment/gui-engine -n eci-sandboxes

deploy-cloud: init
	@echo "☁️ [CLOUD] Deploying Git SHA: $(CLOUD_TAG) from registry $(REGISTRY)"
	kubectl set image deployment/eci-gateway gateway=$(REGISTRY)/eci-gateway:$(CLOUD_TAG) -n eci-system
	kubectl set image deployment/eci-orchestrator orchestrator=$(REGISTRY)/eci-orchestrator:$(CLOUD_TAG) -n eci-system
	kubectl set env deployment/eci-orchestrator CPP_ENGINE_TAG=$(CLOUD_TAG) IMAGE_REGISTRY="$(REGISTRY)" -n eci-system
	kubectl rollout status deployment/eci-gateway -n eci-system
	kubectl rollout status deployment/eci-orchestrator -n eci-system
	@echo "☁️ [CLOUD] Updating sandbox engine images..."
	kubectl set image daemonset/sandbox-image-prepuller cpp-prepuller=$(REGISTRY)/eci-cpp-engine:$(CLOUD_TAG) -n eci-sandboxes
	kubectl set image daemonset/sandbox-image-prepuller python-prepuller=$(REGISTRY)/eci-python-engine:$(CLOUD_TAG) -n eci-sandboxes
	kubectl set image deployment/prewarmed-cpp-engine secure-engine=$(REGISTRY)/eci-cpp-engine:$(CLOUD_TAG) -n eci-sandboxes
	kubectl set image deployment/prewarmed-python-engine secure-engine=$(REGISTRY)/eci-python-engine:$(CLOUD_TAG) -n eci-sandboxes
	kubectl set image deployment/prewarmed-jvm-engine secure-engine=$(REGISTRY)/eci-jvm-engine:$(CLOUD_TAG) -n eci-sandboxes
	kubectl set image deployment/prewarmed-dotnet-engine secure-engine=$(REGISTRY)/eci-dotnet-engine:$(CLOUD_TAG) -n eci-sandboxes
	kubectl set image deployment/prewarmed-go-engine secure-engine=$(REGISTRY)/eci-go-engine:$(CLOUD_TAG) -n eci-sandboxes
	kubectl set image deployment/prewarmed-rust-engine secure-engine=$(REGISTRY)/eci-rust-engine:$(CLOUD_TAG) -n eci-sandboxes
	kubectl set image deployment/prewarmed-node-engine secure-engine=$(REGISTRY)/eci-node-engine:$(CLOUD_TAG) -n eci-sandboxes
	kubectl rollout status deployment/prewarmed-cpp-engine -n eci-sandboxes
	kubectl rollout status deployment/prewarmed-python-engine -n eci-sandboxes
	kubectl rollout status deployment/prewarmed-jvm-engine -n eci-sandboxes
	kubectl rollout status deployment/prewarmed-dotnet-engine -n eci-sandboxes
	kubectl rollout status deployment/prewarmed-go-engine -n eci-sandboxes
	kubectl rollout status deployment/prewarmed-rust-engine -n eci-sandboxes
	kubectl rollout status deployment/prewarmed-node-engine -n eci-sandboxes

# 🚀 The Master Hybrid Command
all:
	@echo "🌐 Checking Cloud Registry ($(REGISTRY)) for git SHA: $(CLOUD_TAG)..."
	@docker pull $(REGISTRY)/eci-gateway:$(CLOUD_TAG) > /dev/null 2>&1; \
	if [ $$? -eq 0 ]; then \
		echo "✅ Cloud image found! Deploying from GHCR..."; \
		$(MAKE) clean deploy-cloud; \
	else \
		echo "⚠️ Cloud image NOT FOUND or offline."; \
		read -p "Shift to Local Development Build? [y/N]: " ans; \
		if [ "$$ans" = "y" ] || [ "$$ans" = "Y" ]; then \
			echo "🚀 Initiating Local Build + Deploy..."; \
			$(MAKE) all-local; \
		else \
			echo "❌ Deployment aborted."; exit 1; \
		fi; \
	fi

# 🔨 Force-Local: Build -> Save TAG -> Clean -> Deploy (reads TAG from file)
all-local:
	@echo "🚀 [FORCE LOCAL] Build + Deploy with frozen TAG..."
	$(MAKE) build-local
	$(MAKE) clean
	$(MAKE) deploy-local

# ============================================================
# Dev Workflow (Phase 1.5 - Hot Reloading)
# ============================================================
dev-tunnel:
	@echo "🚇 Establishing Redis Tunnel (Port 6379)..."
	@kubectl port-forward svc/redis-svc 6379:6379 -n eci-system || echo "Tunnel may already be running"

dev-gateway:
	@echo "🚀 Starting Local API Gateway (Hot Reload Enabled)..."
	$env:REDIS_HOST="localhost" ; $env:ENV="development" ; cd src/api-gateway && uvicorn main:app --app-dir src --host 0.0.0.0 --port 8080 --reload

dev-orchestrator:
	@echo "🚀 Starting Local Environment Orchestrator (Hot Reload Enabled)..."
	$env:REDIS_HOST="localhost" ; $env:ENV="development" ; cd src/environment-orchestrator && python src/worker.py

dev:
	@echo "🌐 Launching Phase 1.5 Master Dev Environment..."
	@powershell -ExecutionPolicy Bypass -File scripts/start_dev.ps1

tst:
	@echo "🧹 Flushing Redis Queue to prevent processing old payloads..."
	kubectl exec deployment/redis -n eci-system -- redis-cli flushall || true
	@echo "🌱 Re-seeding PodCatalog to Redis Cache..."
	python scripts/seed_db.py
	@echo "🚀 Running the e2e test script..."
	$env:PYTHONIOENCODING="utf-8" ; python test_e2e_gauntlet.py || set PYTHONIOENCODING=utf-8 && python test_e2e_gauntlet.py

# ============================================================
# Garbage Collection (Phase 1.1 & 1.2)
# ============================================================
clean-images:
	@echo "🧹 Pruning dangling Docker images to reclaim disk space..."
	docker image prune -f
	@echo "✅ Local image cleanup complete."

clean-pods:
	@echo "🧹 Deleting dead (Completed/Failed) pods from eci-sandboxes..."
	kubectl delete pods --field-selector status.phase=Succeeded -n eci-sandboxes || true
	kubectl delete pods --field-selector status.phase=Failed -n eci-sandboxes || true
	@echo "✅ Pod cleanup complete."