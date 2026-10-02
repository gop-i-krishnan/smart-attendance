from datetime import time
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.class_ import Class
from app.models.timetable import Timetable
from app.schemas.timetable import TimetableCreate


def _time_overlaps(start_a: time, end_a: time, start_b: time, end_b: time) -> bool:
    return max(start_a, start_b) < min(end_a, end_b)


def _validate_timetable(db: Session, timetable: TimetableCreate, exclude_id: int | None = None):
    if timetable.start_time >= timetable.end_time:
        raise HTTPException(status_code=400, detail="End time must be after start time")

    class_obj = db.query(Class).filter(Class.id == timetable.class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")

    existing_entries = db.query(Timetable).filter(
        Timetable.day_of_week == timetable.day_of_week,
        Timetable.id != (exclude_id or -1),
    ).all()

    for entry in existing_entries:
        teacher_conflict = entry.class_.teacher_id == class_obj.teacher_id
        room_conflict = bool(entry.room and timetable.room and entry.room == timetable.room)
        if teacher_conflict or room_conflict:
            if _time_overlaps(
                timetable.start_time,
                timetable.end_time,
                entry.start_time,
                entry.end_time,
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Timetable conflict detected for the same teacher or room at the same time",
                )


def get_timetable_by_id(db: Session, timetable_id: int):
    return db.query(Timetable).filter(Timetable.id == timetable_id).first()


def get_timetables_by_class(db: Session, class_id: int):
    return db.query(Timetable).filter(Timetable.class_id == class_id).all()


def get_timetables_by_teacher(db: Session, teacher_id: int):
    return db.query(Timetable).join(Class).filter(Class.teacher_id == teacher_id).all()


def get_all_timetables(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Timetable).offset(skip).limit(limit).all()


def create_timetable(db: Session, timetable: TimetableCreate):
    _validate_timetable(db, timetable)
    db_timetable = Timetable(
        class_id=timetable.class_id,
        day_of_week=timetable.day_of_week,
        start_time=timetable.start_time,
        end_time=timetable.end_time,
        room=timetable.room,
    )
    db.add(db_timetable)
    db.commit()
    db.refresh(db_timetable)
    return db_timetable


def update_timetable(db: Session, timetable_id: int, timetable: TimetableCreate):
    existing = get_timetable_by_id(db, timetable_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Timetable entry not found")
    _validate_timetable(db, timetable, exclude_id=timetable_id)
    existing.class_id = timetable.class_id
    existing.day_of_week = timetable.day_of_week
    existing.start_time = timetable.start_time
    existing.end_time = timetable.end_time
    existing.room = timetable.room
    db.commit()
    db.refresh(existing)
    return existing


def delete_timetable(db: Session, timetable_id: int):
    timetable = get_timetable_by_id(db, timetable_id)
    if not timetable:
        raise HTTPException(status_code=404, detail="Timetable entry not found")
    db.delete(timetable)
    db.commit()
    return True
