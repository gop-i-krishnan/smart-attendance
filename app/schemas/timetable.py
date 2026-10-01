from pydantic import BaseModel
from datetime import time
from typing import Optional

class TimetableBase(BaseModel):
    class_id: int
    day_of_week: str
    start_time: time
    end_time: time
    room: Optional[str] = None

class TimetableCreate(TimetableBase):
    pass

class TimetableResponse(TimetableBase):
    id: int

    class Config:
        from_attributes = True
