from sqlalchemy.orm import Session

from app.models.enrollment import Enrollment


def get_active_enrollment(
    db: Session,
    student_id: int,
    class_id: int,
):
    return (
        db.query(Enrollment)
        .filter(
            Enrollment.student_id == student_id,
            Enrollment.class_id == class_id,
            Enrollment.is_active.is_(True),
        )
        .first()
    )


def get_enrollment(
    db: Session,
    enrollment_id: int,
):
    return (
        db.query(Enrollment)
        .filter(Enrollment.id == enrollment_id)
        .first()
    )


def get_enrollment_by_student_and_class(
    db: Session,
    student_id: int,
    class_id: int,
):
    return (
        db.query(Enrollment)
        .filter(
            Enrollment.student_id == student_id,
            Enrollment.class_id == class_id,
        )
        .first()
    )


def get_all_enrollments(db: Session):
    return db.query(Enrollment).all()


def create_enrollment(
    db: Session,
    student_id: int,
    class_id: int,
):
    enrollment = Enrollment(
        student_id=student_id,
        class_id=class_id,
        is_active=True,
    )

    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)

    return enrollment


def reactivate_enrollment(
    db: Session,
    enrollment: Enrollment,
):
    enrollment.is_active = True

    db.commit()
    db.refresh(enrollment)

    return enrollment


def deactivate_enrollment(
    db: Session,
    enrollment: Enrollment,
):
    enrollment.is_active = False

    db.commit()
    db.refresh(enrollment)

    return enrollment