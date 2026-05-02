import csv
import io
from fastapi import APIRouter, Depends, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.repositories import attendance_repository, student_repository
from app.services.attendance_service import get_student_summary

router = APIRouter()

@router.get("/student/{student_id}/csv")
def export_student_csv(
    student_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Export a student's attendance as a downloadable CSV file"""
    records = attendance_repository.get_attendance_by_student(db, student_id)

    # Create CSV in memory — no file needed on disk
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow(["ID", "Student ID", "Class ID", "Date", "Status"])

    # Data rows
    for r in records:
        writer.writerow([r.id, r.student_id, r.class_id, r.date, r.status])

    csv_content = output.getvalue()

    # Return as downloadable file
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=student_{student_id}_attendance.csv"
        }
    )

@router.get("/summary/all")
def all_students_summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get attendance summary for every student"""
    students = student_repository.get_all_students(db)
    summaries = []
    for student in students:
        summary = get_student_summary(db, student.id)
        summary["roll_number"] = student.roll_number
        summary["department"] = student.department
        summaries.append(summary)
    return summaries