from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.class_ import Class
from app.models.enrollment import Enrollment
from app.models.user import UserRole
from app.repositories import user_repository


def get_class_by_id(db: Session, class_id: int):
    return db.query(Class).filter(Class.id == class_id).first()


def get_all_classes(db: Session):
    return db.query(Class).all()


def get_accessible_classes(db: Session, current_user):
    """
    Return only the classes the current user is authorized to see.

    Admin:
        Can see all classes.

    Teacher:
        Can see classes assigned to that teacher.

    Student:
        Can see classes in which the student has an active enrollment.
    """

    if current_user.role == UserRole.admin:
        return db.query(Class).all()

    if current_user.role == UserRole.teacher:
        return (
            db.query(Class)
            .filter(Class.teacher_id == current_user.id)
            .all()
        )

    if current_user.role == UserRole.student:
        student = current_user.student

        if not student:
            return []

        return (
            db.query(Class)
            .join(
                Enrollment,
                Enrollment.class_id == Class.id
            )
            .filter(
                Enrollment.student_id == student.id,
                Enrollment.is_active.is_(True),
            )
            .all()
        )

    return []


def create_class(
    db: Session,
    name: str,
    code: str,
    department: str,
    teacher_id: int
):
    teacher = user_repository.get_user_by_id(db, teacher_id)

    if not teacher:
        raise HTTPException(
            status_code=404,
            detail="Teacher not found"
        )

    if teacher.role != UserRole.teacher:
        raise HTTPException(
            status_code=400,
            detail="Assigned user is not a teacher"
        )

    class_ = Class(
        name=name,
        code=code,
        department=department,
        teacher_id=teacher_id
    )

    db.add(class_)
    db.commit()
    db.refresh(class_)

    return class_