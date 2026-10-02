from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.repositories import notice_repository
from app.schemas.notice import NoticeCreate, NoticeOut

router = APIRouter()


@router.get("/", response_model=list[NoticeOut])
def list_notices(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return notice_repository.get_active_notices(db)


@router.post("/", response_model=NoticeOut)
def create_notice(
    notice: NoticeCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    return notice_repository.create_notice(db, notice, created_by=current_user.id)


@router.get("/{notice_id}", response_model=NoticeOut)
def get_notice(
    notice_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    notice = notice_repository.get_notice_by_id(db, notice_id)
    if not notice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found")
    return notice