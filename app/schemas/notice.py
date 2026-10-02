from datetime import datetime
from pydantic import BaseModel


class NoticeCreate(BaseModel):
    title: str
    message: str
    notice_type: str = "Notice"


class NoticeOut(NoticeCreate):
    id: int
    created_by: int
    created_at: datetime
    is_active: bool = True

    class Config:
        from_attributes = True
