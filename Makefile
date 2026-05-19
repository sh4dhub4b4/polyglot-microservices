# Hybrid Smart Makefile
TAG := $(shell date +%s)

# ⚠️ TUMI EKHAANE TOMAR GITHUB USERNAME DEBE (lowercase e)
GITHUB_USER := sh4dhub4b4
REGISTRY := ghcr.io/$(GITHUB_USER)/polyglot-microservices

.PHONY: init build-local clean deploy-local try-cloud deploy-cloud all tst

init:
	@echo "🛠️ Checking and Initializing Kubernetes Namespaces..."
	@kubectl create namespace eci-system --dry-run=client -o yaml | kubectl apply -f -
	@kubectl create namespace eci-sandboxes --dry-run=client -o yaml | kubectl apply -f -
	@if [ -d "k8s" ]; then kubectl apply -f k8s/; fi

build-local:
	@echo "📦 [LOCAL] Building images with unique tag: v$(TAG)..."
	docker build -t eci-python-engine:v$(TAG) -f src/cpp-processing-engine/Dockerfile.python src/cpp-processing-engine/
	docker build -t eci-cpp-engine:v$(TAG) -f src/cpp-processing-engine/Dockerfile.cpp src/cpp-processing-engine/
	docker build -t eci-orchestrator:v$(TAG) -f src/environment-orchestrator/Dockerfile src/environment-orchestrator/
	docker build -t eci-gateway:v$(TAG) -f src/api-gateway/Dockerfile src/api-gateway/

clean:
	@echo "🧹 Cleaning old sandboxes..."
	@kubectl delete pods --all -n eci-sandboxes --ignore-not-found=true

deploy-local: init
	@echo "🔄 [LOCAL] Injecting Local Images to K8s..."
	kubectl set image deployment/eci-gateway gateway=eci-gateway:v$(TAG) -n eci-system
	kubectl set image deployment/eci-orchestrator orchestrator=eci-orchestrator:v$(TAG) -n eci-system
	kubectl set env deployment/eci-orchestrator CPP_ENGINE_TAG=v$(TAG) IMAGE_REGISTRY="" -n eci-system
	kubectl rollout status deployment/eci-gateway -n eci-system
	kubectl rollout status deployment/eci-orchestrator -n eci-system

deploy-cloud: init
	@echo "☁️ [CLOUD] Injecting GHCR Images to K8s..."
	kubectl set image deployment/eci-gateway gateway=$(REGISTRY)/eci-gateway:latest -n eci-system
	kubectl set image deployment/eci-orchestrator orchestrator=$(REGISTRY)/eci-orchestrator:latest -n eci-system
	kubectl set env deployment/eci-orchestrator CPP_ENGINE_TAG=latest IMAGE_REGISTRY="$(REGISTRY)" -n eci-system
	kubectl rollout status deployment/eci-gateway -n eci-system
	kubectl rollout status deployment/eci-orchestrator -n eci-system

# 🚀 The Master Hybrid Command
all:
	@echo "🌐 Checking Cloud Registry ($(REGISTRY)) for latest gateway image..."
	@docker pull $(REGISTRY)/eci-gateway:latest > /dev/null 2>&1; \
	if [ $$? -eq 0 ]; then \
		echo "✅ Cloud images accessible! Deploying from GHCR..."; \
		$(MAKE) clean deploy-cloud; \
	else \
		echo "⚠️ Cloud images NOT FOUND or you are offline."; \
		read -p "Shift to Local Development Build? [y/N]: " ans; \
		if [ "$$ans" = "y" ] || [ "$$ans" = "Y" ]; then \
			echo "🚀 Initiating Local Build Sequence..."; \
			$(MAKE) build-local clean deploy-local; \
		else \
			echo "❌ Deployment aborted by user."; exit 1; \
		fi; \
	fi

# 🔨 The Force-Local Command (Intentional Bypass)
all-local:
	@echo "🚀 [FORCE LOCAL] Bypassing cloud check. Initiating Intentional Local Build Sequence..."
	$(MAKE) build-local clean deploy-local

tst:
	@echo "🚀 Running the e2e test script..."
	python test_e2e_gauntlet.py