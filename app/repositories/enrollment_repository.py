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