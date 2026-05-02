from sqlalchemy.orm import Session
from datetime import date as date_type
from app.models.attendance import Attendance, AttendanceStatus

def get_attendance_record(db: Session, student_id: int,
                          class_id: int, att_date: date_type):
    return db.query(Attendance).filter(
        Attendance.student_id == student_id,
        Attendance.class_id == class_id,
        Attendance.date == att_date
    ).first()

def create_attendance(db: Session, student_id: int, class_id: int,
                      att_date: date_type, att_status: AttendanceStatus):
    record = Attendance(
        student_id=student_id,
        class_id=class_id,
        date=att_date,
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

def get_attendance_by_class(db: Session, class_id: int):
    return db.query(Attendance).filter(
        Attendance.class_id == class_id
    ).all()

def get_attendance_by_class_and_date(db: Session, class_id: int,
                                      att_date: date_type):
    return db.query(Attendance).filter(
        Attendance.class_id == class_id,
        Attendance.date == att_date
    ).all()