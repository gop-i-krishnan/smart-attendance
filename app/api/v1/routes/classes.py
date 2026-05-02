from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.schemas.class_ import ClassCreate, ClassOut
from app.repositories import class_repository

router = APIRouter()

@router.post("/", response_model=ClassOut)
def create_class(
    data: ClassCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):
    return class_repository.create_class(
        db, data.name, data.code, data.department, data.teacher_id
    )

@router.get("/", response_model=list[ClassOut])
def list_classes(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return class_repository.get_all_classes(db)