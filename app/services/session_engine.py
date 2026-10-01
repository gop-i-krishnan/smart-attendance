from sqlalchemy.orm import Session
from datetime import date as date_type
from typing import List

from app.models.timetable import Timetable
from app.models.academic_event import AcademicEvent, EventType
from app.models.class_session import ClassSession, SessionType
from app.repositories import timetable_repository, academic_event_repository, class_session_repository
from app.schemas.class_session import ClassSessionCreate

def generate_daily_sessions(db: Session, target_date: date_type):
    """
    Core Engine logic: 
    1. Check if the target_date is a holiday.
    2. Fetch the timetable for the day of the week.
    3. Generate actual class sessions.
    """
    
    # 1. Find if there are any holidays or institution-wide events on this date
    events = db.query(AcademicEvent).filter(
        AcademicEvent.start_date <= target_date,
        AcademicEvent.end_date >= target_date
    ).all()
    
    is_holiday = any(event.event_type == EventType.holiday for event in events)
    
    # Get the day of week string (e.g., "Monday")
    day_name = target_date.strftime("%A")
    
    # 2. Get all timetable entries for this day of the week
    planned_timetables = db.query(Timetable).filter(Timetable.day_of_week == day_name).all()
    
    created_sessions = []
    
    for timetable in planned_timetables:
        # Check if session already exists for this timetable and date to prevent duplicates
        existing_session = db.query(ClassSession).filter(
            ClassSession.timetable_id == timetable.id,
            ClassSession.date == target_date
        ).first()
        
        if existing_session:
            continue
            
        # 3. Generate Session Reality
        # If it's a holiday, the class is cancelled automatically
        session_type = SessionType.cancelled if is_holiday else SessionType.regular
        
        # Create the session record
        new_session = ClassSessionCreate(
            class_id=timetable.class_id,
            timetable_id=timetable.id,
            actual_teacher_id=timetable.class_.teacher_id, # Defaults to the planned teacher
            date=target_date,
            start_time=timetable.start_time,
            end_time=timetable.end_time,
            room=timetable.room,
            session_type=session_type
        )
        
        db_session = class_session_repository.create_class_session(db, new_session)
        created_sessions.append(db_session)
        
    return created_sessions
