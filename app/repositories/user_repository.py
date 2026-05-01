from sqlalchemy.orm import Session
from app.models.user import User

def get_user_by_email(db: Session, email: str) -> User | None:
    """Find a user by their email address"""
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Find a user by their ID"""
    return db.query(User).filter(User.id == user_id).first()

def create_user(db: Session, full_name: str, email: str,
                hashed_password: str, role) -> User:
    """Insert a new user row into the database"""
    user = User(
        full_name=full_name,
        email=email,
        hashed_password=hashed_password,
        role=role
    )
    db.add(user)       # stage the insert
    db.commit()        # execute it
    db.refresh(user)   # reload to get the auto-generated id
    return user