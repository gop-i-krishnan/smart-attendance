from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.services.assistant_service import build_ai_assistant_summary

router = APIRouter()


@router.get("/")
def get_assistant_summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return build_ai_assistant_summary(db, current_user.role, current_user.id)