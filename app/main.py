from fastapi import FastAPI
from app.config import settings
from app.api.v1.routes import health

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="A clean, role-based attendance management system"
)

app.include_router(
    health.router,
    prefix="/api/v1",
    tags=["Health"]
)

@app.get("/")
def root():
    return {"message": "Welcome to Smart Attendance Platform"}