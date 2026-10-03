from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_student_access, require_teacher
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
        class_session_id=data.class_session_id,
        att_status=data.status,
        requesting_user=current_user,
    )

@router.get("/student/{student_id}", response_model=list[AttendanceOut])
def get_student_attendance(
    student_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_student_access)
):
    return attendance_repository.get_attendance_by_student(db, student_id)

@router.get("/student/{student_id}/summary", response_model=AttendanceSummary)
def get_student_summary(
    student_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_student_access)
):
    return attendance_service.get_student_summary(db, student_id)

@router.get("/session/{class_session_id}", response_model=list[AttendanceOut])
def get_session_attendance(
    class_session_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_teacher)
):
    return attendance_repository.get_attendance_by_class_session(
        db, class_session_id
    )