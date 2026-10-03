from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    Date,
    Enum,
    DateTime,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base

class AttendanceStatus(str, enum.Enum):
    present = "present"
    absent = "absent"
    late = "late"

class Attendance(Base):
    __tablename__ = "attendance"

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "class_session_id",
            name="uq_attendance_student_session",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Which student
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)

    # Which class session did they attend
    class_session_id = Column(
        Integer,
        ForeignKey("class_sessions.id"),
        nullable=False
    )

    # Was the student present, absent, or late
    status = Column(Enum(AttendanceStatus), nullable=False)

    # When was this record created
    marked_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("Student", back_populates="attendance_records")
    class_session = relationship("ClassSession", back_populates="attendance_records")