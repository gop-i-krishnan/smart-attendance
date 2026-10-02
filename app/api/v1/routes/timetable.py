from fastapi import APIRouter, Depends, HTTPException
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

@router.get("/", response_model=list[TimetableResponse])
def list_timetables(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return timetable_repository.get_all_timetables(db, skip=skip, limit=limit)

@router.get("/{timetable_id}", response_model=TimetableResponse)
def get_timetable_by_id(
    timetable_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    timetable = timetable_repository.get_timetable_by_id(db, timetable_id)
    if not timetable:
        raise HTTPException(status_code=404, detail="Timetable entry not found")
    return timetable

@router.put("/{timetable_id}", response_model=TimetableResponse)
def update_timetable(
    timetable_id: int,
    timetable: TimetableCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):
    return timetable_repository.update_timetable(db, timetable_id, timetable)

@router.delete("/{timetable_id}")
def delete_timetable(
    timetable_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):
    timetable_repository.delete_timetable(db, timetable_id)
    return {"detail": "Timetable entry deleted"}

@router.get("/class/{class_id}", response_model=list[TimetableResponse])
def get_class_timetable(
    class_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return timetable_repository.get_timetables_by_class(db, class_id)

@router.get("/teacher/{teacher_id}", response_model=list[TimetableResponse])
def get_teacher_timetable(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return timetable_repository.get_timetables_by_teacher(db, teacher_id)

@router.get("/today", response_model=list[TimetableResponse])
def get_today_timetable(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    from datetime import datetime
    today_name = datetime.now().strftime("%A")
    queryset = db.query(__import__('app.models.timetable', fromlist=['Timetable']).Timetable).filter(
        __import__('app.models.timetable', fromlist=['Timetable']).Timetable.day_of_week == today_name
    ).all()
    if current_user.role == 'teacher':
        from app.models.class_ import Class
        filtered = []
        for entry in queryset:
            if entry.class_.teacher_id == current_user.id:
                filtered.append(entry)
        return filtered
    return queryset
