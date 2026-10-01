from sqlalchemy.orm import Session
from app.models.attendance import Attendance, AttendanceStatus

def get_attendance_record(db: Session, student_id: int, class_session_id: int):
    return db.query(Attendance).filter(
        Attendance.student_id == student_id,
        Attendance.class_session_id == class_session_id
    ).first()

def create_attendance(db: Session, student_id: int, class_session_id: int, att_status: AttendanceStatus):
    record = Attendance(
        student_id=student_id,
        class_session_id=class_session_id,
        status=att_status
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

def get_attendance_by_student(db: Session, student_id: int):
    return db.query(Attendance).filter(
        Attendance.student_id == student_id
    ).all()

def get_attendance_by_class_session(db: Session, class_session_id: int):
    return db.query(Attendance).filter(
        Attendance.class_session_id == class_session_id
    ).all()