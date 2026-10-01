from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional
from app.models.workflows import LeaveType, WorkflowStatus

class LeaveRequestBase(BaseModel):
    leave_type: LeaveType
    from_date: date
    to_date: date
    reason: str

class LeaveRequestCreate(LeaveRequestBase):
    pass

class LeaveRequestOut(LeaveRequestBase):
    id: int
    student_id: int
    status: WorkflowStatus
    applied_at: datetime
    approved_by: Optional[int] = None

    class Config:
        from_attributes = True

class AttendanceCorrectionBase(BaseModel):
    class_session_id: int
    reason: str

class AttendanceCorrectionCreate(AttendanceCorrectionBase):
    pass

class AttendanceCorrectionOut(AttendanceCorrectionBase):
    id: int
    student_id: int
    status: WorkflowStatus
    requested_at: datetime
    approved_by: Optional[int] = None

    class Config:
        from_attributes = True
