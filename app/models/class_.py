from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Class(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)          # e.g. "Data Structures"
    code = Column(String, unique=True, nullable=False)  # e.g. "CS301"
    department = Column(String, nullable=False)

    # Which teacher owns this class
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    teacher = relationship("User")
    attendance_records = relationship("Attendance", back_populates="class_")