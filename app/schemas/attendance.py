from pydantic import BaseModel
from app.models.attendance import AttendanceStatus

class AttendanceCreate(BaseModel):
    student_id: int
    class_session_id: int
    status: AttendanceStatus

class AttendanceOut(BaseModel):
    id: int
    student_id: int
    class_session_id: int
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