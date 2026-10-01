from sqlalchemy.orm import Session
from app.models.timetable import Timetable
from app.schemas.timetable import TimetableCreate

def get_timetable_by_id(db: Session, timetable_id: int):
    return db.query(Timetable).filter(Timetable.id == timetable_id).first()

def get_timetables_by_class(db: Session, class_id: int):
    return db.query(Timetable).filter(Timetable.class_id == class_id).all()

def create_timetable(db: Session, timetable: TimetableCreate):
    db_timetable = Timetable(
        class_id=timetable.class_id,
        day_of_week=timetable.day_of_week,
        start_time=timetable.start_time,
        end_time=timetable.end_time,
        room=timetable.room
    )
    db.add(db_timetable)
    db.commit()
    db.refresh(db_timetable)
    return db_timetable
