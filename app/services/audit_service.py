from sqlalchemy.orm import Session
from app.schemas.audit_log import AuditLogCreate
from app.repositories import audit_log_repository

def log_action(
    db: Session,
    action: str,
    user_id: int = None,
    entity_type: str = None,
    entity_id: str = None,
    ip_address: str = None,
    remarks: str = None
):
    """
    Log a security-sensitive action.
    """
    log_in = AuditLogCreate(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        ip_address=ip_address,
        remarks=remarks
    )
    return audit_log_repository.create_audit_log(db, log_in)
