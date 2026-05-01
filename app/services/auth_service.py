from sqlalchemy.orm import Session
from app.repositories import user_repository
from app.core.security import hash_password, verify_password, create_access_token
from app.schemas.user import UserCreate
from fastapi import HTTPException, status

def register_user(db: Session, user_data: UserCreate):
    """Register a new user — checks for duplicate email first"""
    existing = user_repository.get_user_by_email(db, user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    hashed = hash_password(user_data.password)
    return user_repository.create_user(
        db,
        full_name=user_data.full_name,
        email=user_data.email,
        hashed_password=hashed,
        role=user_data.role
    )

def login_user(db: Session, email: str, password: str):
    """Verify credentials and return a JWT token"""
    user = user_repository.get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    token = create_access_token({"sub": user.email, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}