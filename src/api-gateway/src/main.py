from fastapi import FastAPI
from presentation.execution_ws import router as execution_router
from presentation.routers import router as enroll_router
from presentation.teacher_router import router as teacher_router
from presentation.metrics_router import router as metrics_router
from infrastructure.database import engine, Base
import infrastructure.orm_models # Ensure models are loaded

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ECI API Gateway")

# Include the WebSocket router for execution
app.include_router(execution_router)
app.include_router(enroll_router)
app.include_router(teacher_router)
app.include_router(metrics_router)

@app.get("/")
def health_check():
    return {"status": "Gateway is alive"}