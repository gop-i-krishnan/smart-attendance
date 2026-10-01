from pydantic import BaseModel
from datetime import date, time
from typing import Optional
from app.models.class_session import SessionType

class ClassSessionBase(BaseModel):
    class_id: int
    timetable_id: Optional[int] = None
    actual_teacher_id: int
    date: date
    start_time: time
    end_time: time
    room: Optional[str] = None
    session_type: SessionType

class ClassSessionCreate(ClassSessionBase):
    pass

class ClassSessionOut(ClassSessionBase):
    id: int

    class Config:
        from_attributes = True
