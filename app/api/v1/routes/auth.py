from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.user import UserCreate, UserOut
from app.schemas.token import Token
from app.services import auth_service

router = APIRouter()

@router.post("/register", response_model=UserOut)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user account"""
    return auth_service.register_user(db, user_data)

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login with email and password.
    OAuth2PasswordRequestForm expects 'username' field — we treat it as email.
    """
    return auth_service.login_user(db, form_data.username, form_data.password)