from sqlalchemy.orm import Session
from app.models.academic_event import AcademicEvent
from app.schemas.academic_event import AcademicEventCreate

def get_event_by_id(db: Session, event_id: int):
    return db.query(AcademicEvent).filter(AcademicEvent.id == event_id).first()

def get_all_events(db: Session):
    return db.query(AcademicEvent).all()

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
    return db_event
