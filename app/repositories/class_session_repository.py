from sqlalchemy.orm import Session
from datetime import date as date_type
from app.models.class_session import ClassSession
from app.schemas.class_session import ClassSessionCreate

def get_class_session(db: Session, session_id: int):
    return db.query(ClassSession).filter(ClassSession.id == session_id).first()

def create_class_session(db: Session, data: ClassSessionCreate):
    session_record = ClassSession(
        class_id=data.class_id,
        timetable_id=data.timetable_id,
        actual_teacher_id=data.actual_teacher_id,
        date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
        room=data.room,
        session_type=data.session_type
    )
    db.add(session_record)
    db.commit()
    db.refresh(session_record)
    return session_record

def get_sessions_by_class_and_date(db: Session, class_id: int, date: date_type):
    return db.query(ClassSession).filter(
        ClassSession.class_id == class_id,
        ClassSession.date == date
    ).all()
