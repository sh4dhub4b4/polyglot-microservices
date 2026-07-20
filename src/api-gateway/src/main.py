from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from presentation.execution_ws import router as execution_router
from presentation.routers import router as enroll_router
from presentation.teacher_router import router as teacher_router
from presentation.metrics_router import router as metrics_router
from presentation.academic_router import router as academic_router
from presentation.auth_router import router as auth_router
from infrastructure.database import engine, Base
import infrastructure.orm_models # Ensure models are loaded

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ECI API Gateway",
    description="""
**Polyglot Microservices Platform** — Curriculum-Aware Academic Cloud Infrastructure.

Provides secure, zero-trust, high-performance backend for executing untrusted student code natively.
Multi-tenant SaaS platform with JWT authentication, role-based access control, and real-time interactive & batch code execution via WebSockets.

## Authentication
- **Bearer JWT** via `Authorization` header (primary)
- **X-User-ID / X-User-Role** headers (legacy fallback)

## Execution Modes
- **Batch**: Submit code → backend executes → returns result (one-way)
- **Interactive**: Real-time bidirectional stdin/stdout streaming via WebSocket relay

## Key Features
- Auto-grading with hidden test cases
- Prometheus metrics
- Compute credit billing system
- Custom pod environments for faculty
- WebAssembly (WASM) lightweight payload offloading
    """,
    version="1.0.0",
    contact={
        "name": "Polyglot Team",
        "url": "https://github.com/sh4dhub4b4/polyglot-microservices-platform",
    },
    openapi_tags=[
        {"name": "Auth", "description": "User registration, login, and JWT token management"},
        {"name": "Academic", "description": "Teacher & student endpoints: courses, assignments, submissions, grading, billing"},
        {"name": "Enrollments", "description": "Student course enrollment management"},
        {"name": "Teacher Dashboard", "description": "Custom sandbox environment creation for faculty"},
        {"name": "Observability", "description": "Prometheus metrics endpoint"},
        {"name": "Health", "description": "Service health checks and status"},
    ],
)

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the WebSocket router for execution
app.include_router(execution_router)
app.include_router(enroll_router)
app.include_router(teacher_router)
app.include_router(metrics_router)
app.include_router(academic_router)
app.include_router(auth_router)

# Serve the HTML dummy frontend from the frontend-web/static directory
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend-web", "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", summary="Redirect to login page", tags=["Health"])
def redirect_to_login():
    return RedirectResponse(url="/static/login.html")

@app.get("/api/health", summary="Health check", tags=["Health"])
def api_health():
    return {"status": "Gateway is alive"}