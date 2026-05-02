from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date as date_type
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_teacher
from app.schemas.attendance import AttendanceCreate, AttendanceOut, AttendanceSummary
from app.services import attendance_service
from app.repositories import attendance_repository

router = APIRouter()

@router.post("/mark", response_model=AttendanceOut)
def mark_attendance(
    data: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_teacher)
):
    return attendance_service.mark_attendance(
        db,
        student_id=data.student_id,
        class_id=data.class_id,
        attendance_date=data.date,
        att_status=data.status
    )

@router.get("/student/{student_id}", response_model=list[AttendanceOut])
def get_student_attendance(
    student_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return attendance_repository.get_attendance_by_student(db, student_id)

@router.get("/student/{student_id}/summary", response_model=AttendanceSummary)
def get_student_summary(
    student_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return attendance_service.get_student_summary(db, student_id)

@router.get("/class/{class_id}/date/{att_date}", response_model=list[AttendanceOut])
def get_class_attendance_by_date(
    class_id: int,
    att_date: date_type,
    db: Session = Depends(get_db),
    current_user=Depends(require_teacher)
):
    return attendance_repository.get_attendance_by_class_and_date(
        db, class_id, att_date
    )