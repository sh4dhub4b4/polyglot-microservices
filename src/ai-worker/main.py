# pyrefly: ignore [missing-import]
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "Infrastructure is operational!"}