from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)

    # ForeignKey links this to the users table
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    roll_number = Column(String, unique=True, nullable=False)
    department = Column(String, nullable=False)
    semester = Column(Integer, nullable=False)

    # Relationships
    user = relationship("User", back_populates="student")
    attendance_records = relationship("Attendance", back_populates="student")