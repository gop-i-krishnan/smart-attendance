from sqlalchemy.orm import Session
from datetime import date as date_type
from fastapi import HTTPException
from starlette import status as http_status
from app.repositories import attendance_repository, student_repository, class_repository
from app.models.attendance import AttendanceStatus

def mark_attendance(db: Session, student_id: int, class_id: int,
                    attendance_date: date_type, att_status: AttendanceStatus):

    student = student_repository.get_student_by_id(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    class_ = class_repository.get_class_by_id(db, class_id)
    if not class_:
        raise HTTPException(status_code=404, detail="Class not found")

    existing = attendance_repository.get_attendance_record(
        db, student_id, class_id, attendance_date
    )
    if existing:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="Attendance already marked for this student on this date"
        )

    return attendance_repository.create_attendance(
        db, student_id, class_id, attendance_date, att_status
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