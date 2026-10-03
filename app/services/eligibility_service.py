from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, exists, select

from app.models.class_ import Class
from app.models.student import Student
from app.models.enrollment import Enrollment


def get_classes_for_student_filter(student: Student):
    """
    Build a SQLAlchemy filter for classes accessible to one student.

    Eligibility is granted through either:

    1. Implicit cohort matching:
       - class semester is not NULL
       - department matches
       - semester matches
       - class section is NULL OR matches student's section

    OR

    2. Active explicit Enrollment for the student.

    A class with semester=NULL requires explicit Enrollment.
    """

    implicit_condition = and_(
        Class.semester.isnot(None),
        Class.department == student.department,
        Class.semester == student.semester,
        or_(
            Class.section.is_(None),
            Class.section == student.section,
        ),
    )

    active_enrollment_exists = exists(
        select(Enrollment.id).where(
            and_(
                Enrollment.student_id == student.id,
                Enrollment.class_id == Class.id,
                Enrollment.is_active.is_(True),
            )
        )
    )

    return or_(
        implicit_condition,
        active_enrollment_exists,
    )


def get_students_for_class_filter(class_record: Class):
    """
    Build a SQLAlchemy filter for students eligible for one class.

    Eligibility is granted through either:

    1. Implicit cohort matching:
       - class semester is not NULL
       - department matches
       - semester matches
       - class section is NULL OR matches student's section

    OR

    2. Active explicit Enrollment for the class.

    A class with semester=NULL requires explicit Enrollment.
    """

    implicit_condition = and_(
        class_record.semester is not None,
        Student.department == class_record.department,
        Student.semester == class_record.semester,
        or_(
            class_record.section is None,
            Student.section == class_record.section,
        ),
    )

    active_enrollment_exists = exists(
        select(Enrollment.id).where(
            and_(
                Enrollment.student_id == Student.id,
                Enrollment.class_id == class_record.id,
                Enrollment.is_active.is_(True),
            )
        )
    )

    # If semester is NULL, implicit eligibility must be disabled.
    if class_record.semester is None:
        return active_enrollment_exists

    return or_(
        implicit_condition,
        active_enrollment_exists,
    )


def check_student_class_eligibility(
    db: Session,
    student_id: int,
    class_id: int,
) -> bool:
    """
    Check whether a specific student is eligible for a specific class.

    Eligibility comes from either:
    - implicit cohort matching
    - active explicit Enrollment
    """

    student = (
        db.query(Student)
        .filter(Student.id == student_id)
        .first()
    )

    if not student:
        return False

    class_record = (
        db.query(Class)
        .filter(Class.id == class_id)
        .first()
    )

    if not class_record:
        return False

    # Check implicit cohort eligibility.
    if class_record.semester is not None:
        department_matches = (
            student.department == class_record.department
        )

        semester_matches = (
            student.semester == class_record.semester
        )

        section_matches = (
            class_record.section is None
            or student.section == class_record.section
        )

        if (
            department_matches
            and semester_matches
            and section_matches
        ):
            return True

    # Check explicit active enrollment.
    active_enrollment = (
        db.query(Enrollment.id)
        .filter(
            Enrollment.student_id == student_id,
            Enrollment.class_id == class_id,
            Enrollment.is_active.is_(True),
        )
        .first()
    )

    return active_enrollment is not None