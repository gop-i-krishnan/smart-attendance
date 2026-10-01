"""
Schedule Change Service — handles substitutions, cancellations, compensatory sessions.
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.class_session import ClassSession, SessionType
from app.models.user import UserRole


def substitute_session(db: Session, session_id: int, new_teacher_id: int, requesting_user) -> ClassSession:
    """Replace the teacher for a given class session."""
    session = db.query(ClassSession).filter(ClassSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.session_type == SessionType.cancelled:
        raise HTTPException(status_code=400, detail="Cannot substitute a cancelled session")
    session.actual_teacher_id = new_teacher_id
    session.session_type = SessionType.substitute
    db.commit()
    db.refresh(session)
    return session


def cancel_session(db: Session, session_id: int) -> ClassSession:
    """Cancel an existing class session."""
    session = db.query(ClassSession).filter(ClassSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.session_type = SessionType.cancelled
    db.commit()
    db.refresh(session)
    return session
