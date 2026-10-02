from sqlalchemy.orm import Session
from app.models.notice import Notice
from app.schemas.notice import NoticeCreate


def create_notice(db: Session, notice: NoticeCreate, created_by: int):
    db_notice = Notice(
        title=notice.title,
        message=notice.message,
        notice_type=notice.notice_type,
        created_by=created_by,
    )
    db.add(db_notice)
    db.commit()
    db.refresh(db_notice)
    return db_notice


def get_active_notices(db: Session):
    return db.query(Notice).filter(Notice.is_active == True).order_by(Notice.created_at.desc()).all()


def get_notice_by_id(db: Session, notice_id: int):
    return db.query(Notice).filter(Notice.id == notice_id).first()
