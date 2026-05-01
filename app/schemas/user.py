from pydantic import BaseModel, EmailStr
from app.models.user import UserRole

class UserCreate(BaseModel):
    """What the client sends when registering"""
    full_name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.student

class UserOut(BaseModel):
    """What we send back — never include password"""
    id: int
    full_name: str
    email: str
    role: UserRole
    is_active: bool

    class Config:
        from_attributes = True  # allows converting SQLAlchemy model to this schema