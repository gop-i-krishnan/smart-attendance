from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.schemas.student import StudentCreate, StudentOut
from app.repositories import student_repository

router = APIRouter()

@router.post("/", response_model=StudentOut)
def create_student(
    data: StudentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):
    return student_repository.create_student(
        db, data.user_id, data.roll_number, data.department, data.semester
    )

@router.get("/", response_model=list[StudentOut])
def list_students(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return student_repository.get_all_students(db)