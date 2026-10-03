from sqlalchemy import Column, Integer, String, Date, Enum, ForeignKey
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base

class EventType(str, enum.Enum):
    holiday = "holiday"
    exam = "exam"
    other = "other"

class AcademicEvent(Base):
    __tablename__ = "academic_events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    event_type = Column(Enum(EventType), default=EventType.other, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    creator = relationship("User")
