from sqlalchemy.orm import Session
from fastapi import HTTPException
from starlette import status as http_status
from app.repositories import attendance_repository, student_repository, class_session_repository
from app.models.attendance import AttendanceStatus
from app.models.class_session import SessionType
from app.models.user import UserRole

def mark_attendance(
    db: Session,
    student_id: int,
    class_session_id: int,
    att_status: AttendanceStatus,
    requesting_user=None,
):
    student = student_repository.get_student_by_id(db, student_id)
    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    session_record = class_session_repository.get_class_session(
        db, class_session_id
    )
    if not session_record:
        raise HTTPException(
            status_code=404,
            detail="Class session not found"
        )

    # 1. Prevent attendance for cancelled sessions
    if session_record.session_type == SessionType.cancelled:
        raise HTTPException(
            status_code=400,
            detail="Attendance cannot be marked for a cancelled session"
        )

    # 2. Attendance can only be marked while the session is open
    if not session_record.is_open:
        raise HTTPException(
            status_code=400,
            detail="Attendance cannot be marked when the session is closed"
        )

    # 3. Only the assigned teacher or an admin can mark attendance
    if requesting_user is not None:
        if (
            requesting_user.role != UserRole.admin
            and session_record.actual_teacher_id != requesting_user.id
        ):
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to mark attendance for this session"
            )

    # 4. Prevent duplicate attendance
    existing = attendance_repository.get_attendance_record(
        db,
        student_id,
        class_session_id
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Attendance already marked for this student in this session"
        )

    # 5. Create attendance
    return attendance_repository.create_attendance(
        db,
        student_id,
        class_session_id,
        att_status
    )

def get_student_summary(db: Session, student_id: int):
    records = attendance_repository.get_attendance_by_student(db, student_id)

    if not records:
        return {
            "student_id": student_id,
            "total_classes": 0,
            "present": 0,
            "absent": 0,
            "late": 0,
            "percentage": 0.0
        }

    total = len(records)
    present = sum(1 for r in records if r.status == AttendanceStatus.present)
    absent = sum(1 for r in records if r.status == AttendanceStatus.absent)
    late = sum(1 for r in records if r.status == AttendanceStatus.late)
    percentage = round(((present + late) / total) * 100, 2)

    return {
        "student_id": student_id,
        "total_classes": total,
        "present": present,
        "absent": absent,
        "late": late,
        "percentage": percentage
    }