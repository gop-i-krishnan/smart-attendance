from sqlalchemy import Column, Integer, ForeignKey, Date, Enum, DateTime
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

    id = Column(Integer, primary_key=True, index=True)

    # Which student
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)

    # Which class
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)

    # What date was this taken
    date = Column(Date, nullable=False)

    # Was the student present, absent, or late
    status = Column(Enum(AttendanceStatus), nullable=False)

    # When was this record created
    marked_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    student = relationship("Student", back_populates="attendance_records")
    class_ = relationship("Class", back_populates="attendance_records")