from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.class_ import Class
from app.models.student import Student
from app.models.user import UserRole

from app.repositories import user_repository

from app.services.eligibility_service import (
    get_classes_for_student_filter,
    get_students_for_class_filter,
)


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
        Can see classes for which they are eligible through either:
        - department + semester + section matching
        - active explicit Enrollment
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
            .filter(get_classes_for_student_filter(student))
            .all()
        )

    return []


def get_class_roster(
    db: Session,
    class_id: int,
    current_user,
):
    """
    Return the eligible student roster for a class.

    Admin:
        Can view any class roster.

    Teacher:
        Can view the roster only for classes assigned to them.

    Student:
        Cannot view class rosters.
    """

    class_record = get_class_by_id(db, class_id)

    if not class_record:
        raise HTTPException(
            status_code=404,
            detail="Class not found",
        )

    if current_user.role == UserRole.admin:
        pass

    elif current_user.role == UserRole.teacher:
        if class_record.teacher_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to view this class roster",
            )

    else:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view class rosters",
        )

    return (
        db.query(Student)
        .filter(get_students_for_class_filter(class_record))
        .all()
    )


def create_class(
    db: Session,
    name: str,
    code: str,
    department: str,
    teacher_id: int,
    semester: int | None = None,
    section: str | None = None,
):
    teacher = user_repository.get_user_by_id(db, teacher_id)

    if not teacher:
        raise HTTPException(
            status_code=404,
            detail="Teacher not found",
        )

    if teacher.role != UserRole.teacher:
        raise HTTPException(
            status_code=400,
            detail="Assigned user is not a teacher",
        )

    class_ = Class(
        name=name,
        code=code,
        department=department,
        teacher_id=teacher_id,
        semester=semester,
        section=section,
    )

    db.add(class_)
    db.commit()
    db.refresh(class_)

    return class_