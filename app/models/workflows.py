from sqlalchemy import Column, Integer, String, Date, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base

class WorkflowStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

class LeaveType(str, enum.Enum):
    sick = "sick"
    duty = "duty"
    emergency = "emergency"
    other = "other"

class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    leave_type = Column(Enum(LeaveType), default=LeaveType.other, nullable=False)
    from_date = Column(Date, nullable=False)
    to_date = Column(Date, nullable=False)
    reason = Column(String, nullable=False)
    
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.pending, nullable=False)
    
    applied_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    student = relationship("Student")
    approver = relationship("User")

class AttendanceCorrection(Base):
    __tablename__ = "attendance_corrections"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    class_session_id = Column(Integer, ForeignKey("class_sessions.id"), nullable=False)
    
    reason = Column(String, nullable=False)
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.pending, nullable=False)
    
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    student = relationship("Student")
    class_session = relationship("ClassSession")
    approver = relationship("User")
