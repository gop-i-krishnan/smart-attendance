from pydantic import BaseModel
from datetime import date
from typing import Optional
from app.models.academic_event import EventType

class AcademicEventBase(BaseModel):
    title: str
    description: Optional[str] = None
    event_type: EventType
    start_date: date
    end_date: date

class AcademicEventCreate(AcademicEventBase):
    pass

class AcademicEventResponse(AcademicEventBase):
    id: int
    created_by: int

    class Config:
        from_attributes = True
