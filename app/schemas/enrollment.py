from datetime import datetime

from pydantic import BaseModel


class EnrollmentCreate(BaseModel):
    student_id: int
    class_id: int


class EnrollmentOut(BaseModel):
    id: int
    student_id: int
    class_id: int
    enrolled_at: datetime
    is_active: bool

    class Config:
        from_attributes = True