# ============================================================
# Phase 1.5: Dev Workflow Launcher (Hot Reloading)
# ============================================================
Write-Host "[DEV] Launching Polyglot Microservices in DEV mode..." -ForegroundColor Cyan

# 1. Cleanup Ghost Processes
Write-Host "[CLEANUP] Terminating any ghost port-forward processes..." -ForegroundColor Yellow
Stop-Process -Name "kubectl" -Force -ErrorAction SilentlyContinue

# 2. Scale Down & Release Ports from Docker Desktop
Write-Host "[K8s] Scaling down K8s pods and releasing port 8080..." -ForegroundColor Yellow
kubectl scale deployment eci-gateway --replicas=0 -n eci-system
kubectl scale deployment eci-orchestrator --replicas=0 -n eci-system
# By converting the LoadBalancer to ClusterIP, Docker Desktop immediately releases port 8080 to Windows!
kubectl patch svc eci-gateway -n eci-system -p '{\"spec\": {\"type\": \"ClusterIP\"}}'

# 3. Launch Redis Tunnel in background
Write-Host "[K8s] Establishing Redis Tunnel to K8s (Port 6379)..." -ForegroundColor Yellow
Start-Process -NoNewWindow -FilePath "kubectl" -ArgumentList "port-forward", "svc/redis-svc", "6379:6379", "-n", "eci-system"

Start-Sleep -Seconds 2

# 3. Launch API Gateway in a new PowerShell window
Write-Host "[DEV] Launching API Gateway (Port 8080)..." -ForegroundColor Green
Start-Process "powershell" -ArgumentList "-NoExit", "-Command", "`$env:REDIS_HOST='localhost'; `$env:ENV='development'; cd src\api-gateway; uvicorn main:app --app-dir src --host 0.0.0.0 --port 8080 --reload"

# 4. Launch Environment Orchestrator in a new PowerShell window
Write-Host "[DEV] Launching Environment Orchestrator Worker..." -ForegroundColor Green
Start-Process "powershell" -ArgumentList "-NoExit", "-Command", "`$env:REDIS_HOST='localhost'; `$env:ENV='development'; cd src\environment-orchestrator; python src\worker.py"

Write-Host "[SUCCESS] Dev Environment Successfully Launched!" -ForegroundColor Green
Write-Host "To test: run 'make tst'" -ForegroundColor Cyan
Write-Host "To exit: Close the newly opened PowerShell windows and press Ctrl+C to kill the tunnel." -ForegroundColor Cyan
