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
    return timetable_repository.get_accessible_timetables(
    db,
    current_user,
)

@router.get("/{timetable_id}", response_model=TimetableResponse)
def get_timetable_by_id(
    timetable_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    timetable = timetable_repository.get_timetable_by_id(
        db,
        timetable_id,
    )

    if not timetable:
        raise HTTPException(
            status_code=404,
            detail="Timetable entry not found",
        )

    if not timetable_repository.can_access_timetable(
        db,
        timetable,
        current_user,
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to access this timetable",
        )

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
    timetables = timetable_repository.get_timetables_by_class(
        db,
        class_id,
    )

    if current_user.role == "admin":
        return timetables

    if current_user.role == "teacher":
        if not timetables:
            return []

        if timetables[0].class_.teacher_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to access this class timetable",
            )

        return timetables

    if current_user.role == "student":
        if not current_user.student:
            raise HTTPException(
                status_code=403,
                detail="Student profile not found",
            )

        has_enrollment = timetable_repository.get_accessible_timetables(
            db,
            current_user,
        )

        accessible_class_ids = {
            timetable.class_id
            for timetable in has_enrollment
        }

        if class_id not in accessible_class_ids:
            raise HTTPException(
                status_code=403,
                detail="You are not enrolled in this class",
            )

        return timetables

    raise HTTPException(
        status_code=403,
        detail="You are not authorized to access this class timetable",
    )

@router.get("/teacher/{teacher_id}", response_model=list[TimetableResponse])
def get_teacher_timetable(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if current_user.role == "admin":
        return timetable_repository.get_timetables_by_teacher(
            db,
            teacher_id,
        )

    if current_user.role == "teacher":
        if teacher_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only access your own timetable",
            )

        return timetable_repository.get_timetables_by_teacher(
            db,
            current_user.id,
        )

    raise HTTPException(
        status_code=403,
        detail="Students cannot access teacher timetables",
    )

@router.get("/today", response_model=list[TimetableResponse])
def get_today_timetable(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    from datetime import datetime
    from app.models.timetable import Timetable

    today_name = datetime.now().strftime("%A")

    queryset = (
        db.query(Timetable)
        .filter(Timetable.day_of_week == today_name)
        .all()
    )

    if current_user.role == "admin":
        return queryset

    if current_user.role == "teacher":
        return [
            entry
            for entry in queryset
            if entry.class_.teacher_id == current_user.id
        ]

    if current_user.role == "student":
        if not current_user.student:
            return []

        accessible = timetable_repository.get_accessible_timetables(
            db,
            current_user,
        )

        accessible_ids = {entry.id for entry in accessible}

        return [
            entry
            for entry in queryset
            if entry.id in accessible_ids
        ]

    return []
