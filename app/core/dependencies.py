from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.security import decode_access_token
from app.core.database import get_db
from app.repositories import user_repository

# Tells FastAPI where to find the token (the /login endpoint)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Decode the JWT token and return the current logged-in user"""
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    email = payload.get("sub")
    user = user_repository.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

def require_admin(current_user=Depends(get_current_user)):
    """Only allow admin users"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    return current_user

def require_teacher(current_user=Depends(get_current_user)):
    """Only allow teachers and admins"""
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Teachers only")
    return current_user