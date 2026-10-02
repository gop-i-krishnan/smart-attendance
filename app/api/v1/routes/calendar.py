from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.schemas.academic_event import AcademicEventCreate, AcademicEventResponse
from app.repositories import academic_event_repository

router = APIRouter()

@router.post("/", response_model=AcademicEventResponse)
def create_event(
    event: AcademicEventCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):
    return academic_event_repository.create_event(db, event, created_by=current_user.id)

@router.get("/", response_model=list[AcademicEventResponse])
def list_events(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return academic_event_repository.get_all_events(db)

@router.get("/{event_id}", response_model=AcademicEventResponse)
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    event = academic_event_repository.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@router.put("/{event_id}", response_model=AcademicEventResponse)
def update_event(
    event_id: int,
    event: AcademicEventCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):
    existing = academic_event_repository.get_event_by_id(db, event_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Event not found")
    existing.title = event.title
    existing.description = event.description
    existing.event_type = event.event_type
    existing.start_date = event.start_date
    existing.end_date = event.end_date
    existing.created_by = current_user.id
    db.commit()
    db.refresh(existing)
    return existing

@router.delete("/{event_id}")
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):
    event = academic_event_repository.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(event)
    db.commit()
    return {"detail": "Event deleted"}

@router.get("/range")
def get_events_in_range(
    start_date: date = Query(..., alias="from"),
    end_date: date = Query(..., alias="to"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return academic_event_repository.get_events_in_range(db, start_date, end_date)

@router.get("/upcoming")
def get_upcoming_events(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return academic_event_repository.get_upcoming_events(db, days=days)
