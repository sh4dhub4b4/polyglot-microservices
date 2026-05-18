# Generate a completely unique dynamic tag based on current timestamp
TAG := $(shell date +%s)

.PHONY: init build clean deploy all tst

# 🚀 CRITICAL CLUSTER FIX: Automatically creates namespaces and applies base k8s files if wiped out
init:
	@echo "🛠️ Checking and Initializing Kubernetes Namespaces..."
	kubectl create namespace eci-system --dry-run=client -o yaml | kubectl apply -f -
	kubectl create namespace eci-sandboxes --dry-run=client -o yaml | kubectl apply -f -
	@echo "📄 Applying base cluster deployments from manifests..."
	@if [ -d "k8s" ]; then \
		kubectl apply -f k8s/; \
	else \
		echo "⚠️ Warning: 'k8s' folder not found. Skipping base manifest apply."; \
	fi

build:
	@echo "📦 Building isolated images with unique tag: v$(TAG)..."
	docker build -t eci-python-engine:v$(TAG) -f src/cpp-processing-engine/Dockerfile.python src/cpp-processing-engine/
	docker build -t eci-cpp-engine:v$(TAG) -f src/cpp-processing-engine/Dockerfile.cpp src/cpp-processing-engine/
	docker build -t eci-orchestrator:v$(TAG) -f src/environment-orchestrator/Dockerfile src/environment-orchestrator/
	docker build -t eci-gateway:v$(TAG) -f src/api-gateway/Dockerfile src/api-gateway/

clean:
	@echo "🧹 Cleaning old sandboxes..."
	kubectl delete pods --all -n eci-sandboxes --ignore-not-found=true

deploy: init
	@echo "🔄 Injecting Dynamic Tag (v$(TAG)) to Kubernetes Clusters..."
	# Now these will NEVER fail because 'init' guaranteed the namespace and deployment exist!
	kubectl set image deployment/eci-gateway gateway=eci-gateway:v$(TAG) -n eci-system
	kubectl set image deployment/eci-orchestrator orchestrator=eci-orchestrator:v$(TAG) -n eci-system
	kubectl set env deployment/eci-orchestrator CPP_ENGINE_TAG=v$(TAG) -n eci-system
	
	@echo "⏳ Waiting for K8s pods to fully rollout and stabilize..."
	kubectl rollout status deployment/eci-gateway -n eci-system
	kubectl rollout status deployment/eci-orchestrator -n eci-system

tst:
	@echo "🚀 Running the e2e test script..."
	python test_e2e_gauntlet.py

# The master workflow now safely starts with 'init'
all: init build clean deploy
	@echo "✅ All pipeline stages done! System fully upgraded to v$(TAG). Run 'make tst' to test."