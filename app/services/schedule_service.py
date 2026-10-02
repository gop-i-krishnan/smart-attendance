"""
Schedule Change Service — handles substitutions, cancellations, compensatory sessions.
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.class_session import ClassSession, SessionType
from app.models.user import UserRole


def substitute_session(
    db: Session,
    session_id: int,
    new_teacher_id: int,
    requesting_user
) -> ClassSession:
    """Replace the teacher for a given class session."""

    session = db.query(ClassSession).filter(
        ClassSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    if session.session_type == SessionType.cancelled:
        raise HTTPException(
            status_code=400,
            detail="Cannot substitute a cancelled session"
        )

    # Only the currently assigned teacher or an admin
    # may substitute this session.
    if (
        requesting_user.role != UserRole.admin
        and session.actual_teacher_id != requesting_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to modify this session"
        )

    session.actual_teacher_id = new_teacher_id
    session.session_type = SessionType.substitute
    session.status = "Rescheduled"
    session.is_open = False

    db.commit()
    db.refresh(session)

    return session


def cancel_session(
    db: Session,
    session_id: int,
    requesting_user
) -> ClassSession:
    """Cancel an existing class session."""

    session = db.query(ClassSession).filter(
        ClassSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    # Only the currently assigned teacher or an admin
    # may cancel this session.
    if (
        requesting_user.role != UserRole.admin
        and session.actual_teacher_id != requesting_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to modify this session"
        )

    session.session_type = SessionType.cancelled
    session.status = "Cancelled"
    session.is_open = False

    db.commit()
    db.refresh(session)

    return session
