import csv
import io
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_student_access, require_teacher
from app.repositories import student_repository, attendance_repository
from app.services import analytics_service
router = APIRouter()
@router.get("/risk/all")
def all_risk_report(
    db: Session = Depends(get_db),
    current_user=Depends(require_teacher)
):
    """Full risk-sorted analytics for all students."""
    return analytics_service.get_all_risk_report(db, current_user)
@router.get("/student/{student_id}")
def student_analytics(
    student_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_student_access)
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
    if current_user.role == "teacher":
        from app.models.class_ import Class
        from fastapi import HTTPException
        cls = db.query(Class).filter(Class.id == class_id).first()
        if not cls or cls.teacher_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this class")
    return analytics_service.get_class_analytics(db, class_id)
@router.get("/student/{student_id}/csv")
def export_student_csv(
    student_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_student_access)
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
from app.core.dependencies import require_admin
from app.models.student import Student
from app.models.class_session import ClassSession
from app.models.attendance import Attendance, AttendanceStatus
@router.get("/overview")
def overview_analytics(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):
    total_students = db.query(Student).count()
    total_sessions = db.query(ClassSession).count()
    total_attendance = db.query(Attendance).count()
    present_count = db.query(Attendance).filter(Attendance.status.in_([AttendanceStatus.present, AttendanceStatus.late])).count()
    absent_count = db.query(Attendance).filter(Attendance.status == AttendanceStatus.absent).count()
    percentage = round((present_count / total_attendance) * 100, 2) if total_attendance > 0 else 0.0
    return {
        "total_students": total_students,
        "total_sessions": total_sessions,
        "total_attendance_records": total_attendance,
        "present_count": present_count,
        "absent_count": absent_count,
        "overall_percentage": percentage
    }
@router.get("/department")
def department_analytics(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):
    from sqlalchemy import func
    # Per-department counts using separate scalar queries (SQLAlchemy 1.x compatible)
    dept_rows = db.query(Student.department).distinct().all()
    result = []
    for (dept,) in dept_rows:
        total = db.query(func.count(Attendance.id)).join(Student).filter(
            Student.department == dept
        ).scalar() or 0
        present = db.query(func.count(Attendance.id)).join(Student).filter(
            Student.department == dept,
            Attendance.status.in_([AttendanceStatus.present, AttendanceStatus.late])
        ).scalar() or 0
        pct = round((present / total) * 100, 2) if total > 0 else 0.0
        result.append({
            "department": dept,
            "total_records": total,
            "present_records": present,
            "percentage": pct
        })
    return result
