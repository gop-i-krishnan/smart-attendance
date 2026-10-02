from datetime import timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.academic_event import AcademicEvent, EventType
from app.models.class_session import ClassSession, SessionType
from app.schemas.academic_event import AcademicEventCreate


def get_event_by_id(db: Session, event_id: int):
    return db.query(AcademicEvent).filter(AcademicEvent.id == event_id).first()


def get_all_events(db: Session):
    return db.query(AcademicEvent).all()


def get_events_in_range(db: Session, start_date, end_date):
    return db.query(AcademicEvent).filter(
        AcademicEvent.start_date <= end_date,
        AcademicEvent.end_date >= start_date,
    ).all()


def get_upcoming_events(db: Session, days: int = 30):
    from datetime import date
    today = date.today()
    future = today + timedelta(days=days)
    return db.query(AcademicEvent).filter(
        AcademicEvent.start_date >= today,
        AcademicEvent.start_date <= future,
    ).order_by(AcademicEvent.start_date).all()


def cancel_sessions_for_event(db: Session, event_id: int):
    event = get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    sessions = db.query(ClassSession).filter(
        ClassSession.date >= event.start_date,
        ClassSession.date <= event.end_date,
    ).all()

    affected = 0
    for session in sessions:
        if session.session_type == SessionType.cancelled and session.status == "Cancelled":
            affected += 1
            continue
        session.session_type = SessionType.cancelled
        session.status = "Cancelled"
        session.is_open = False
        affected += 1

    db.commit()
    return affected


def create_event(db: Session, event: AcademicEventCreate, created_by: int):
    db_event = AcademicEvent(
        title=event.title,
        description=event.description,
        event_type=event.event_type,
        start_date=event.start_date,
        end_date=event.end_date,
        created_by=created_by
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    if event.event_type == EventType.holiday:
        cancel_sessions_for_event(db, db_event.id)
    return db_event
