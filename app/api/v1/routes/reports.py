"""
Legacy reports router — kept for backwards compatibility.
New analytics are served through /api/v1/analytics/
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.repositories import student_repository
from app.services import analytics_service

router = APIRouter()

@router.get("/summary/all")
def all_students_summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Summary for all students — used by old dashboard.html"""
    return analytics_service.get_all_risk_report(db)