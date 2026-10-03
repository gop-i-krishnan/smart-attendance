from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories import (
    enrollment_repository,
    student_repository,
    class_repository,
)


def create_or_reactivate_enrollment(
    db: Session,
    student_id: int,
    class_id: int,
):
    # 1. Verify student exists
    student = student_repository.get_student_by_id(
        db,
        student_id,
    )

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found",
        )

    # 2. Verify class exists
    class_record = class_repository.get_class_by_id(
        db,
        class_id,
    )

    if not class_record:
        raise HTTPException(
            status_code=404,
            detail="Class not found",
        )

    # 3. Check whether this student-class pair already exists
    existing = enrollment_repository.get_enrollment_by_student_and_class(
        db,
        student_id,
        class_id,
    )

    if existing:
        # Already active
        if existing.is_active:
            raise HTTPException(
                status_code=409,
                detail="Student is already enrolled in this class",
            )

        # Existing but inactive → reactivate
        return enrollment_repository.reactivate_enrollment(
            db,
            existing,
        )

    # 4. No previous enrollment → create one
    return enrollment_repository.create_enrollment(
        db,
        student_id,
        class_id,
    )


def deactivate_enrollment(
    db: Session,
    enrollment_id: int,
):
    enrollment = enrollment_repository.get_enrollment(
        db,
        enrollment_id,
    )

    if not enrollment:
        raise HTTPException(
            status_code=404,
            detail="Enrollment not found",
        )

    if not enrollment.is_active:
        raise HTTPException(
            status_code=400,
            detail="Enrollment is already inactive",
        )

    return enrollment_repository.deactivate_enrollment(
        db,
        enrollment,
    )