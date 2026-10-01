from sqlalchemy import Column, Integer, String, Date, Time, Enum, ForeignKey
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base

class SessionType(str, enum.Enum):
    regular = "regular"
    cancelled = "cancelled"
    substitute = "substitute"
    rescheduled = "rescheduled"
    compensatory = "compensatory"

class ClassSession(Base):
    __tablename__ = "class_sessions"

    id = Column(Integer, primary_key=True, index=True)
    
    # The actual class (subject/section combination)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    
    # Optional link to the planned timetable entry
    timetable_id = Column(Integer, ForeignKey("timetables.id"), nullable=True)
    
    # The teacher who ACTUALLY conducted the session
    actual_teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    room = Column(String, nullable=True)
    
    session_type = Column(Enum(SessionType), default=SessionType.regular, nullable=False)
    
    # Relationships
    class_ = relationship("Class")
    timetable = relationship("Timetable")
    actual_teacher = relationship("User")
    attendance_records = relationship("Attendance", back_populates="class_session")
