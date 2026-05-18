from fastapi import FastAPI
from presentation.execution_ws import router as execution_router

app = FastAPI(title="ECI API Gateway")

# Include the WebSocket router for execution
app.include_router(execution_router)

@app.get("/")
def health_check():
    return {"status": "Gateway is alive"}