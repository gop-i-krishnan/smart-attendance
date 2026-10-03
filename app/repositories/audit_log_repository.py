from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogCreate

def create_audit_log(db: Session, log_in: AuditLogCreate) -> AuditLog:
    db_obj = AuditLog(
        user_id=log_in.user_id,
        action=log_in.action,
        entity_type=log_in.entity_type,
        entity_id=log_in.entity_id,
        ip_address=log_in.ip_address,
        remarks=log_in.remarks
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_audit_logs(db: Session, skip: int = 0, limit: int = 100):
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
