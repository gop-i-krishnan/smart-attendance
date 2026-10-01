import csv
import io
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_teacher
from app.repositories import student_repository, attendance_repository
from app.services import analytics_service

router = APIRouter()


@router.get("/risk/all")
def all_risk_report(
    db: Session = Depends(get_db),
    current_user=Depends(require_teacher)
):
    """Full risk-sorted analytics for all students."""
    return analytics_service.get_all_risk_report(db)


@router.get("/student/{student_id}")
def student_analytics(
    student_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Detailed analytics + shortage prediction for a student."""
    data = analytics_service.get_detailed_student_analytics(db, student_id)
    student = student_repository.get_student_by_id(db, student_id)
    if student:
        data["roll_number"] = student.roll_number
        data["department"] = student.department
        data["semester"] = student.semester
        data["full_name"] = student.user.full_name if student.user else ""
    return data


@router.get("/class/{class_id}")
def class_analytics(
    class_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_teacher)
):
    """Per-session attendance rates for a class."""
    return analytics_service.get_class_analytics(db, class_id)


@router.get("/student/{student_id}/csv")
def export_student_csv(
    student_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Export full attendance history as a CSV file."""
    records = attendance_repository.get_attendance_by_student(db, student_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Record ID", "Student ID", "Session ID", "Status"])
    for r in records:
        writer.writerow([r.id, r.student_id, r.class_session_id, r.status])
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=student_{student_id}_attendance.csv"}
    )
