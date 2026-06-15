from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
import prometheus_client
from prometheus_client import Counter, Histogram

router = APIRouter(tags=["Observability"])

# 1. Define the metrics
pod_spawns_total = Counter(
    "polyglot_pod_spawns_total", 
    "Total number of pods spawned", 
    ["course_code", "env_type"]
)

code_execution_seconds = Histogram(
    "polyglot_code_execution_seconds",
    "Time taken to execute code",
    ["env_type"]
)

@router.get("/metrics", response_class=PlainTextResponse)
def metrics():
    # 2. Expose the /metrics endpoint for Prometheus to scrape
    return prometheus_client.generate_latest()
