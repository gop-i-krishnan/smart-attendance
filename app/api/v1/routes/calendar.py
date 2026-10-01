from fastapi import APIRouter, Depends
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
