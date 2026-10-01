from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date as date_type
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_teacher
from app.schemas.class_session import ClassSessionCreate, ClassSessionOut
from app.repositories import class_session_repository

router = APIRouter()

@router.post("/", response_model=ClassSessionOut)
def create_session(
    data: ClassSessionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_teacher)
):
    return class_session_repository.create_class_session(db, data)

@router.get("/class/{class_id}/date/{date}", response_model=list[ClassSessionOut])
def get_sessions(
    class_id: int,
    date: date_type,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return class_session_repository.get_sessions_by_class_and_date(db, class_id, date)

from app.services.session_engine import generate_daily_sessions
from app.services.schedule_service import substitute_session, cancel_session

@router.post("/generate-daily/{target_date}", response_model=list[ClassSessionOut])
def generate_sessions_for_date(
    target_date: date_type,
    db: Session = Depends(get_db),
    current_user=Depends(require_teacher)
):
    """Generates Class Sessions from Timetable, considering holidays."""
    return generate_daily_sessions(db, target_date)

@router.put("/{session_id}/cancel", response_model=ClassSessionOut)
def cancel_class_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_teacher)
):
    """Cancel a class session."""
    return cancel_session(db, session_id)

@router.put("/{session_id}/substitute", response_model=ClassSessionOut)
def substitute_class_session(
    session_id: int,
    new_teacher_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_teacher)
):
    """Assign a substitute teacher to a session."""
    return substitute_session(db, session_id, new_teacher_id, current_user)

@router.get("/all-sessions", response_model=list[ClassSessionOut])
def get_all_sessions(
    db: Session = Depends(get_db),
    current_user=Depends(require_teacher)
):
    """Get all class sessions (for admin/teacher overview)."""
    from app.models.class_session import ClassSession as CS
    return db.query(CS).order_by(CS.date.desc()).limit(100).all()
