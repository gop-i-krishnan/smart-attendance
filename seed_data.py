import os
import asyncio
from datetime import date, time
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password as get_password_hash
from app.models.user import User, UserRole
from app.models.student import Student
from app.models.class_ import Class
from app.models.timetable import Timetable
from app.models.academic_event import AcademicEvent, EventType
from app.models.class_session import ClassSession, SessionType
from app.models.notice import Notice

def seed_data():
    db = SessionLocal()
    
    # 1. Clear existing data (optional, for clean slate testing)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # 2. Create Users (Admin, Teacher, Students)
    admin = User(full_name="Admin User", email="admin@rset.edu", hashed_password=get_password_hash("password"), role=UserRole.admin)
    teacher = User(full_name="Joy George", email="teacher@rset.edu", hashed_password=get_password_hash("password"), role=UserRole.teacher)
    
    db.add_all([admin, teacher])
    db.commit()

    student1 = User(full_name="Dominic B Moyalan", email="student1@rset.edu", hashed_password=get_password_hash("password"), role=UserRole.student)
    student2 = User(full_name="Gopikrishnan D", email="student2@rset.edu", hashed_password=get_password_hash("password"), role=UserRole.student)
    student3 = User(full_name="Alice Smith", email="alice@rset.edu", hashed_password=get_password_hash("password"), role=UserRole.student)
    
    db.add_all([student1, student2, student3])
    db.commit()

    # 3. Create Student Profiles
    s1 = Student(user_id=student1.id, roll_number="U2301079", department="CSE", semester=5)
    s2 = Student(user_id=student2.id, roll_number="U2301098", department="CSE", semester=5)
    s3 = Student(user_id=student3.id, roll_number="U2301000", department="CSE", semester=5)
    
    db.add_all([s1, s2, s3])
    db.commit()

    # 4. Create a Class
    cs_class = Class(name="Advanced Database Systems", code="CS302", department="CSE", teacher_id=teacher.id)
    db.add(cs_class)
    db.commit()

    # 5. Create Timetable for this Class (Assuming today is Monday or Tuesday)
    t1 = Timetable(class_id=cs_class.id, day_of_week="Monday", start_time=time(9, 0), end_time=time(10, 0), room="Room 101")
    t2 = Timetable(class_id=cs_class.id, day_of_week="Tuesday", start_time=time(10, 0), end_time=time(11, 0), room="Room 101")
    t3 = Timetable(class_id=cs_class.id, day_of_week="Wednesday", start_time=time(11, 0), end_time=time(12, 0), room="Room 101")
    t4 = Timetable(class_id=cs_class.id, day_of_week="Thursday", start_time=time(9, 0), end_time=time(10, 0), room="Room 101")
    t5 = Timetable(class_id=cs_class.id, day_of_week="Friday", start_time=time(14, 0), end_time=time(15, 0), room="Room 102")
    
    db.add_all([t1, t2, t3, t4, t5])
    db.commit()

    # 6. Create Academic Events (from RSET Calendar PDF)
    # Using 2025 dates as per calendar
    events = [
        AcademicEvent(title="Semester Begins (S3/S5/S7)", event_type=EventType.other, start_date=date(2025, 6, 30), end_date=date(2025, 6, 30), created_by=admin.id),
        AcademicEvent(title="Internal Audit 1", event_type=EventType.exam, start_date=date(2025, 7, 8), end_date=date(2025, 7, 8), created_by=admin.id),
        AcademicEvent(title="Internal Examination-1", event_type=EventType.exam, start_date=date(2025, 7, 28), end_date=date(2025, 8, 2), created_by=admin.id),
        AcademicEvent(title="Onam Celebration", event_type=EventType.holiday, start_date=date(2025, 8, 27), end_date=date(2025, 8, 27), created_by=admin.id),
        AcademicEvent(title="Abhiyanthriki 2025", event_type=EventType.other, start_date=date(2025, 10, 10), end_date=date(2025, 10, 11), created_by=admin.id),
        AcademicEvent(title="Confluence 2.0", event_type=EventType.other, start_date=date(2025, 9, 27), end_date=date(2025, 9, 27), created_by=admin.id),
        AcademicEvent(title="Semester ends for S3/S5/S7", event_type=EventType.other, start_date=date(2025, 10, 17), end_date=date(2025, 10, 17), created_by=admin.id)
    ]
    db.add_all(events)
    db.commit()

    # 7. Create institutional notices for the dashboard board.
    notices = [
        Notice(title="Semester Begins", message="Welcome to the new academic term. Please check the updated timetable and complete registration tasks.", notice_type="Announcement", created_by=admin.id),
        Notice(title="Internal Exam Updates", message="The internal examination timetable is available. Students should verify their hall allotments and attendance status.", notice_type="Exam Notice", created_by=admin.id),
    ]
    db.add_all(notices)
    db.commit()

    print("Seed data successfully injected into the database!")
    db.close()

if __name__ == "__main__":
    seed_data()
