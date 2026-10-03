from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import date as date_type
from app.models.class_session import ClassSession, SessionType, ClassSessionStatus
from app.schemas.class_session import ClassSessionCreate
from app.models.user import UserRole


def get_class_session(db: Session, session_id: int):
    return db.query(ClassSession).filter(ClassSession.id == session_id).first()


def create_class_session(
    db: Session,
    data: ClassSessionCreate,
    requesting_user
):
    # Teachers can only create sessions assigned to themselves.
    # Admins can create sessions for any teacher.
    if (
        requesting_user.role != UserRole.admin
        and data.actual_teacher_id != requesting_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="Teachers can only create sessions assigned to themselves"
        )

    session_record = ClassSession(
        class_id=data.class_id,
        timetable_id=data.timetable_id,
        actual_teacher_id=data.actual_teacher_id,
        date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
        room=data.room,
        session_type=data.session_type,
        status=ClassSessionStatus.scheduled.value,
        is_open=False,
    )

    db.add(session_record)
    db.commit()
    db.refresh(session_record)

    return session_record


def get_sessions_by_class_and_date(db: Session, class_id: int, date: date_type):
    return db.query(ClassSession).filter(
        ClassSession.class_id == class_id,
        ClassSession.date == date
    ).all()


def get_sessions_by_teacher(db: Session, teacher_id: int):
    return db.query(ClassSession).filter(ClassSession.actual_teacher_id == teacher_id).all()


def get_sessions_for_date(db: Session, target_date: date_type):
    return db.query(ClassSession).filter(ClassSession.date == target_date).all()


def open_session(
    db: Session,
    session_id: int,
    requesting_user
):
    session = get_class_session(db, session_id)

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    if session.session_type == SessionType.cancelled:
        raise HTTPException(
            status_code=400,
            detail="Cancelled sessions cannot be opened"
        )

    # Only the currently assigned teacher or an admin
    # may open this session.
    if (
        requesting_user.role != UserRole.admin
        and session.actual_teacher_id != requesting_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to modify this session"
        )

    session.status = ClassSessionStatus.conducted.value
    session.is_open = True

    db.commit()
    db.refresh(session)

    return session


def close_session(
    db: Session,
    session_id: int,
    requesting_user
):
    session = get_class_session(db, session_id)

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    # Only the currently assigned teacher or an admin
    # may close this session.
    if (
        requesting_user.role != UserRole.admin
        and session.actual_teacher_id != requesting_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to modify this session"
        )

    session.is_open = False
    session.status = ClassSessionStatus.conducted.value

    db.commit()
    db.refresh(session)

    return session


def update_session_status(
    db: Session,
    session_id: int,
    status: str,
    requesting_user
):
    session = get_class_session(db, session_id)

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    # Only the currently assigned teacher or an admin
    # may modify this session's status.
    if (
        requesting_user.role != UserRole.admin
        and session.actual_teacher_id != requesting_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to modify this session"
        )

    try:
        validated_status = ClassSessionStatus(status)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid session status: {status}"
        )

    session.status = validated_status.value

    if validated_status == ClassSessionStatus.cancelled:
        session.session_type = SessionType.cancelled
        session.is_open = False

    elif validated_status == ClassSessionStatus.rescheduled:
        session.session_type = SessionType.rescheduled
        session.is_open = False

    db.commit()
    db.refresh(session)

    return session
