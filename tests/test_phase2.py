from datetime import date, time

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.academic_event import AcademicEvent, EventType
from app.models.attendance import Attendance, AttendanceStatus
from app.models.class_ import Class
from app.models.class_session import ClassSession, SessionType
from app.models.student import Student
from app.models.timetable import Timetable
from app.models.user import User, UserRole
from app.repositories import academic_event_repository, class_session_repository, timetable_repository
from app.repositories.notice_repository import create_notice, get_active_notices
from app.schemas.academic_event import AcademicEventCreate
from app.schemas.class_session import ClassSessionCreate
from app.schemas.notice import NoticeCreate
from app.schemas.timetable import TimetableCreate
from app.services.assistant_service import build_ai_assistant_summary
from seed_demo_data import COURSE_KEY_TO_CODE, FIXED_WEEKLY_PLAN, PERIODS

from app.schemas.user import UserCreate
from app.services import auth_service


@pytest.fixture
def db_session() -> Session:
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    test_session = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = test_session()
    yield db
    db.close()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def _seed_teacher_and_class(db: Session) -> Class:
    teacher = User(
        full_name="Teacher One",
        email="teacher1@example.com",
        hashed_password="hashed",
        role=UserRole.teacher,
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)

    class_obj = Class(
        name="Data Structures",
        code="CS101",
        department="CSE",
        teacher_id=teacher.id,
    )
    db.add(class_obj)
    db.commit()
    db.refresh(class_obj)
    return class_obj


def test_fixed_timetable_covers_both_departments_and_all_periods():
    assert set(FIXED_WEEKLY_PLAN) == {"CSE", "ECE"}
    assert len(PERIODS) == 7
    for weekdays in FIXED_WEEKLY_PLAN.values():
        assert len(weekdays) == 5
        for day_schedule in weekdays:
            assert len(day_schedule) == 7
            assert all(course_key in COURSE_KEY_TO_CODE for course_key in day_schedule)


def test_timetable_conflict_is_rejected(db_session: Session):
    class_obj = _seed_teacher_and_class(db_session)

    existing = Timetable(
        class_id=class_obj.id,
        day_of_week="Monday",
        start_time=time(9, 0),
        end_time=time(10, 0),
        room="A101",
    )
    db_session.add(existing)
    db_session.commit()

    duplicate = TimetableCreate(
        class_id=class_obj.id,
        day_of_week="Monday",
        start_time=time(9, 30),
        end_time=time(10, 30),
        room="A101",
    )

    with pytest.raises(HTTPException):
        timetable_repository.create_timetable(db_session, duplicate)


def test_holiday_event_cancels_sessions_for_matching_date(db_session: Session):
    class_obj = _seed_teacher_and_class(db_session)
    session = ClassSession(
        class_id=class_obj.id,
        timetable_id=None,
        actual_teacher_id=class_obj.teacher_id,
        date=date(2026, 10, 5),
        start_time=time(9, 0),
        end_time=time(10, 0),
        room="A101",
        session_type=SessionType.regular,
    )
    db_session.add(session)
    db_session.commit()

    event = AcademicEventCreate(
        title="Holiday",
        description="Festival",
        event_type=EventType.holiday,
        start_date=date(2026, 10, 5),
        end_date=date(2026, 10, 5),
    )

    result = academic_event_repository.create_event(db_session, event, created_by=class_obj.teacher_id)
    db_session.refresh(result)

    affected = academic_event_repository.cancel_sessions_for_event(db_session, result.id)

    db_session.refresh(session)
    assert affected == 1
    assert session.session_type == SessionType.cancelled


def test_session_can_be_opened_and_closed(db_session: Session):
    class_obj = _seed_teacher_and_class(db_session)
    session = ClassSession(
        class_id=class_obj.id,
        timetable_id=None,
        actual_teacher_id=class_obj.teacher_id,
        date=date(2026, 10, 6),
        start_time=time(11, 0),
        end_time=time(12, 0),
        room="B202",
        session_type=SessionType.regular,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    opened = class_session_repository.open_session(db_session, session.id)
    assert opened.is_open is True

    closed = class_session_repository.close_session(db_session, session.id)
    assert closed.is_open is False


def test_notice_creation_and_ai_summary(db_session: Session):
    admin = User(
        full_name="Admin One",
        email="admin2@example.com",
        hashed_password="hashed",
        role=UserRole.admin,
    )
    db_session.add(admin)
    db_session.commit()

    notice = create_notice(
        db_session,
        NoticeCreate(title="Exam update", message="Internal exam has been rescheduled.", notice_type="Announcement"),
        created_by=admin.id,
    )

    saved = get_active_notices(db_session)
    assert len(saved) == 1
    assert saved[0].id == notice.id

    report = build_ai_assistant_summary(db_session, "admin", admin.id)
    assert "Admin" in report["header"]
    assert "notice" in report["summary"].lower()


def test_student_assistant_summary_uses_attendance_risk(db_session: Session):
    class_obj = _seed_teacher_and_class(db_session)
    student_user = User(
        full_name="Student One",
        email="student1@example.com",
        hashed_password="hashed",
        role=UserRole.student,
    )
    db_session.add(student_user)
    db_session.commit()
    student = Student(
        user_id=student_user.id,
        roll_number="CSE1001",
        department="CSE",
        semester=5,
    )
    db_session.add(student)
    db_session.commit()

    for session_index, attendance_status in enumerate(
        (AttendanceStatus.present, AttendanceStatus.present, AttendanceStatus.absent, AttendanceStatus.absent)
    ):
        session = ClassSession(
            class_id=class_obj.id,
            timetable_id=None,
            actual_teacher_id=class_obj.teacher_id,
            date=date(2026, 9, 1 + session_index),
            start_time=time(9, 0),
            end_time=time(10, 0),
            room="A101",
            session_type=SessionType.regular,
        )
        db_session.add(session)
        db_session.flush()
        db_session.add(
            Attendance(
                student_id=student.id,
                class_session_id=session.id,
                status=attendance_status,
            )
        )
    db_session.commit()

    report = build_ai_assistant_summary(db_session, "student", student_user.id)

    assert report["attendance_percentage"] == 50.0
    assert report["risk"] == "danger"
    assert report["classes_to_recover"] == 4
    assert "50%" in report["summary"]

def test_public_registration_rejects_admin_role(db_session: Session):
    user_data = UserCreate(
        full_name="Unauthorized Admin",
        email="unauthorized-admin@example.com",
        password="StrongPassword123",
        role=UserRole.admin,
    )

    with pytest.raises(HTTPException) as exc_info:
        auth_service.register_user(db_session, user_data)

    assert exc_info.value.status_code == 403