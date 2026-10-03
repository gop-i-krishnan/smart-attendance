from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.config import settings
from app.api.v1.routes import (
    health, auth, attendance, students, classes,
    reports, calendar, timetable, class_session,
    workflows, analytics, notices, assistant, enrollment, admin
)
app = FastAPI(
    title="SecureTrack X — Academic Attendance Platform",
    version="2.0.0",
    description=(
        "Context-aware academic operations platform. "
        "Timetable is the plan; Class Session is the reality; "
        "Attendance belongs to the actual Class Session."
    )
)

app.mount("/static", StaticFiles(directory=Path(__file__).resolve().parent.parent / "static"), name="static")

# ── Core Infrastructure ───────────────────────────────────────────────────────
app.include_router(health.router,    prefix="/api/v1",             tags=["Health"])
app.include_router(auth.router,      prefix="/api/v1/auth",         tags=["Auth"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])

# ── Academic Structure ────────────────────────────────────────────────────────
app.include_router(students.router,  prefix="/api/v1/students",     tags=["Students"])
app.include_router(classes.router,   prefix="/api/v1/classes",      tags=["Classes"])
app.include_router(enrollment.router,   prefix="/api/v1/enrollments",       tags=["Enrollments"],)

# ── Scheduling ────────────────────────────────────────────────────────────────
app.include_router(timetable.router, prefix="/api/v1/timetable",    tags=["Timetable"])
app.include_router(calendar.router,  prefix="/api/v1/calendar",     tags=["Academic Calendar"])
app.include_router(class_session.router, prefix="/api/v1/session",  tags=["Class Session Engine"])
app.include_router(notices.router,    prefix="/api/v1/notices",     tags=["Notices"])
app.include_router(assistant.router,   prefix="/api/v1/assistant",   tags=["AI Assistant"])

# ── Attendance ────────────────────────────────────────────────────────────────
app.include_router(attendance.router, prefix="/api/v1/attendance",  tags=["Attendance"])

# ── Reports & Analytics ───────────────────────────────────────────────────────
app.include_router(reports.router,   prefix="/api/v1/reports",      tags=["Reports (Legacy)"])
app.include_router(analytics.router, prefix="/api/v1/analytics",    tags=["Analytics"])

# ── Workflows ─────────────────────────────────────────────────────────────────
app.include_router(workflows.router, prefix="/api/v1/workflows",    tags=["Workflows"])


# ── Frontend Pages ─────────────────────────────────────────────────────────────
def _render(template_name: str) -> HTMLResponse:
    html = (Path("templates") / template_name).read_text(encoding="utf-8")
    return HTMLResponse(content=html, media_type="text/html; charset=utf-8")

@app.get("/", response_class=HTMLResponse)
def landing():
    return _render("login.html")

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return _render("dashboard.html")

@app.get("/teacher", response_class=HTMLResponse)
def teacher_portal():
    return _render("teacher.html")

@app.get("/student", response_class=HTMLResponse)
def student_portal():
    return _render("student.html")

@app.get("/admin", response_class=HTMLResponse)
def admin_portal():
    return _render("admin.html")