from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.config import settings
from app.api.v1.routes import health, auth, attendance, students, classes, reports
from app.core.database import engine, Base
import app.models

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="A clean, role-based attendance management system"
)

app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(students.router, prefix="/api/v1/students", tags=["Students"])
app.include_router(classes.router, prefix="/api/v1/classes", tags=["Classes"])
app.include_router(attendance.router, prefix="/api/v1/attendance", tags=["Attendance"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])

@app.get("/")
def root():
    return {"message": "Welcome to Smart Attendance Platform"}

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    """Serve the attendance dashboard"""
    html = Path("templates/dashboard.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html, media_type="text/html; charset=utf-8")