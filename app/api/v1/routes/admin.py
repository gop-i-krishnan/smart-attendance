from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserOut
from app.repositories import user_repository, audit_log_repository
from app.schemas.audit_log import AuditLogOut
from app.services.audit_service import log_action


router = APIRouter()


@router.post("/users", response_model=UserOut)
def create_user_by_admin(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """
    Create a user account from the Admin portal.

    Unlike public registration, an administrator can create
    student, teacher, or admin accounts.
    """

    existing = user_repository.get_user_by_email(db, user_data.email)

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    hashed_password = hash_password(user_data.password)

    user = user_repository.create_user(
        db,
        full_name=user_data.full_name,
        email=user_data.email,
        hashed_password=hashed_password,
        role=user_data.role,
    )
    
    log_action(
        db=db,
        action="ADMIN_CREATE_USER",
        user_id=current_user.id,
        entity_type="User",
        entity_id=user.id,
        remarks=f"Admin created {user.role.value} account"
    )
    
    
    return user

@router.get("/audit-logs", response_model=list[AuditLogOut])
def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """View system audit logs."""
    return audit_log_repository.get_audit_logs(db, skip=skip, limit=limit)