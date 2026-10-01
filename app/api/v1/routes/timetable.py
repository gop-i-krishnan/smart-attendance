from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.schemas.timetable import TimetableCreate, TimetableResponse
from app.repositories import timetable_repository

router = APIRouter()

@router.post("/", response_model=TimetableResponse)
def create_timetable(
    timetable: TimetableCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):
    return timetable_repository.create_timetable(db, timetable)

@router.get("/class/{class_id}", response_model=list[TimetableResponse])
def get_class_timetable(
    class_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return timetable_repository.get_timetables_by_class(db, class_id)
