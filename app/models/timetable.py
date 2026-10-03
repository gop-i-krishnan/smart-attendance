from sqlalchemy import Column, Integer, String, Time, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Timetable(Base):
    __tablename__ = "timetables"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    day_of_week = Column(String, nullable=False) # e.g. "Monday"
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    room = Column(String, nullable=True)

    class_ = relationship("Class")
