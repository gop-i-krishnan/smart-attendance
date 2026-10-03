from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.schemas.enrollment import EnrollmentCreate, EnrollmentOut
from app.repositories import enrollment_repository
from app.services import enrollment_service


router = APIRouter()


@router.post("/", response_model=EnrollmentOut)
def create_enrollment(
    data: EnrollmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    return enrollment_service.create_or_reactivate_enrollment(
        db,
        data.student_id,
        data.class_id,
    )


@router.get("/", response_model=list[EnrollmentOut])
def list_enrollments(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    return enrollment_repository.get_all_enrollments(db)


@router.delete("/{enrollment_id}", response_model=EnrollmentOut)
def deactivate_enrollment(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    return enrollment_service.deactivate_enrollment(
        db,
        enrollment_id,
    )