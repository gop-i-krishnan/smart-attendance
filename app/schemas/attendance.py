from pydantic import BaseModel
from datetime import date
from app.models.attendance import AttendanceStatus

class AttendanceCreate(BaseModel):
    student_id: int
    class_id: int
    date: date
    status: AttendanceStatus

class AttendanceOut(BaseModel):
    id: int
    student_id: int
    class_id: int
    date: date
    status: AttendanceStatus

    class Config:
        from_attributes = True

class AttendanceSummary(BaseModel):
    student_id: int
    total_classes: int
    present: int
    absent: int
    late: int
    percentage: float