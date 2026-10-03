from datetime import date, time

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.academic_event import AcademicEvent, EventType
from app.models.attendance import Attendance, AttendanceStatus
from app.models.class_ import Class
from app.models.class_session import ClassSession, SessionType, ClassSessionStatus
from app.models.student import Student
from app.models.timetable import Timetable
from app.models.user import User, UserRole
from app.repositories import academic_event_repository, class_session_repository, timetable_repository, student_repository
from app.repositories.notice_repository import create_notice, get_active_notices
from app.schemas.academic_event import AcademicEventCreate
from app.schemas.class_session import ClassSessionCreate
from app.schemas.notice import NoticeCreate
from app.schemas.timetable import TimetableCreate
from app.services.assistant_service import build_ai_assistant_summary
from app.services.schedule_service import cancel_session, substitute_session
from seed_demo_data import COURSE_KEY_TO_CODE, FIXED_WEEKLY_PLAN, PERIODS

from app.schemas.user import UserCreate
from app.services import auth_service, attendance_service
from app.core.dependencies import get_current_user, require_admin, require_student_access
from app.api.v1.routes.students import list_students



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

    opened = class_session_repository.open_session(db_session, session.id, class_obj.teacher)
    assert opened.is_open is True

    closed = class_session_repository.close_session(db_session, session.id, class_obj.teacher)
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

def test_inactive_user_cannot_use_existing_token(db_session: Session):
    user = User(
        full_name="Disabled User",
        email="disabled@example.com",
        hashed_password="hashed",
        role=UserRole.student,
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = auth_service.create_access_token({"sub": user.email, "role": user.role})

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token, db=db_session)

    assert exc_info.value.status_code == 403
    
def test_student_cannot_list_all_students(db_session: Session):
    student_user = User(
        full_name="Student User",
        email="student-list@example.com",
        hashed_password="hashed",
        role=UserRole.student,
    )
    db_session.add(student_user)
    db_session.commit()
    db_session.refresh(student_user)

    student = Student(
        user_id=student_user.id,
        roll_number="CSE2001",
        department="CSE",
        semester=5,
    )
    db_session.add(student)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        require_admin(student_user)

    assert exc_info.value.status_code == 403

def test_student_cannot_access_another_students_data(db_session: Session):
    student_user = User(
        full_name="Student One",
        email="student-one@example.com",
        hashed_password="hashed",
        role=UserRole.student,
    )

    another_user = User(
        full_name="Student Two",
        email="student-two@example.com",
        hashed_password="hashed",
        role=UserRole.student,
    )

    db_session.add_all([student_user, another_user])
    db_session.commit()
    db_session.refresh(student_user)
    db_session.refresh(another_user)

    student_one = Student(
        user_id=student_user.id,
        roll_number="CSE3001",
        department="CSE",
        semester=5,
    )

    student_two = Student(
        user_id=another_user.id,
        roll_number="CSE3002",
        department="CSE",
        semester=5,
    )

    db_session.add_all([student_one, student_two])
    db_session.commit()
    db_session.refresh(student_one)
    db_session.refresh(student_two)

    current_student = student_repository.get_student_by_user_id(
        db_session,
        student_user.id
    )

    assert current_student.id == student_one.id
    assert current_student.id != student_two.id

    with pytest.raises(HTTPException) as exc_info:
        if student_two.id != current_student.id:
            raise HTTPException(
                status_code=403,
                detail="Students can only access their own data"
            )

    assert exc_info.value.status_code == 403
    
def test_student_cannot_access_another_student_through_dependency(
    db_session: Session
):
    student_user = User(
        full_name="Student Three",
        email="student-three@example.com",
        hashed_password="hashed",
        role=UserRole.student,
    )

    another_user = User(
        full_name="Student Four",
        email="student-four@example.com",
        hashed_password="hashed",
        role=UserRole.student,
    )

    db_session.add_all([student_user, another_user])
    db_session.commit()
    db_session.refresh(student_user)
    db_session.refresh(another_user)

    student_one = Student(
        user_id=student_user.id,
        roll_number="CSE3003",
        department="CSE",
        semester=5,
    )

    student_two = Student(
        user_id=another_user.id,
        roll_number="CSE3004",
        department="CSE",
        semester=5,
    )

    db_session.add_all([student_one, student_two])
    db_session.commit()
    db_session.refresh(student_one)
    db_session.refresh(student_two)

    with pytest.raises(HTTPException) as exc_info:
        require_student_access(
            student_id=student_two.id,
            current_user=student_user,
            db=db_session,
        )

    assert exc_info.value.status_code == 403
    
def test_teacher_cannot_substitute_another_teachers_session(
    db_session: Session
):
    teacher_one = User(
        full_name="Teacher One",
        email="teacher-one@example.com",
        hashed_password="hashed",
        role=UserRole.teacher,
    )

    teacher_two = User(
        full_name="Teacher Two",
        email="teacher-two@example.com",
        hashed_password="hashed",
        role=UserRole.teacher,
    )

    replacement_teacher = User(
        full_name="Replacement Teacher",
        email="replacement@example.com",
        hashed_password="hashed",
        role=UserRole.teacher,
    )

    db_session.add_all([
        teacher_one,
        teacher_two,
        replacement_teacher,
    ])
    db_session.commit()

    db_session.refresh(teacher_one)
    db_session.refresh(teacher_two)
    db_session.refresh(replacement_teacher)

    class_record = Class(
        name="Data Structures",
        code="CS401",
        department="CSE",
        teacher_id=teacher_one.id,
    )

    db_session.add(class_record)
    db_session.commit()
    db_session.refresh(class_record)

    session = ClassSession(
        class_id=class_record.id,
        actual_teacher_id=teacher_one.id,
        date=date.today(),
        start_time=time(10, 0),
        end_time=time(11, 0),
        room="R101",
        session_type=SessionType.regular,
        status=ClassSessionStatus.scheduled.value,
        is_open=False,
    )

    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    with pytest.raises(HTTPException) as exc_info:
        substitute_session(
            db_session,
            session.id,
            replacement_teacher.id,
            teacher_two,
        )

    assert exc_info.value.status_code == 403
    
def test_teacher_cannot_cancel_another_teachers_session(
    db_session: Session
):
    teacher_one = User(
        full_name="Teacher One",
        email="cancel-teacher-one@example.com",
        hashed_password="hashed",
        role=UserRole.teacher,
    )

    teacher_two = User(
        full_name="Teacher Two",
        email="cancel-teacher-two@example.com",
        hashed_password="hashed",
        role=UserRole.teacher,
    )

    db_session.add_all([teacher_one, teacher_two])
    db_session.commit()

    db_session.refresh(teacher_one)
    db_session.refresh(teacher_two)

    class_record = Class(
        name="Operating Systems",
        code="CS402",
        department="CSE",
        teacher_id=teacher_one.id,
    )

    db_session.add(class_record)
    db_session.commit()
    db_session.refresh(class_record)

    session = ClassSession(
        class_id=class_record.id,
        actual_teacher_id=teacher_one.id,
        date=date.today(),
        start_time=time(10, 0),
        end_time=time(11, 0),
        room="R102",
        session_type=SessionType.regular,
        status=ClassSessionStatus.scheduled.value,
        is_open=False,
    )

    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    with pytest.raises(HTTPException) as exc_info:
        cancel_session(
            db_session,
            session.id,
            teacher_two,
        )

    assert exc_info.value.status_code == 403
    
def test_teacher_can_cancel_own_session(db_session: Session):
    teacher = User(
        full_name="Authorized Teacher",
        email="authorized-cancel@example.com",
        hashed_password="hashed",
        role=UserRole.teacher,
    )

    db_session.add(teacher)
    db_session.commit()
    db_session.refresh(teacher)

    class_record = Class(
        name="Database Systems",
        code="CS403",
        department="CSE",
        teacher_id=teacher.id,
    )

    db_session.add(class_record)
    db_session.commit()
    db_session.refresh(class_record)

    session = ClassSession(
        class_id=class_record.id,
        actual_teacher_id=teacher.id,
        date=date.today(),
        start_time=time(10, 0),
        end_time=time(11, 0),
        room="R103",
        session_type=SessionType.regular,
        status=ClassSessionStatus.scheduled.value,
        is_open=False,
    )

    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    cancelled = cancel_session(
        db_session,
        session.id,
        teacher,
    )

    assert cancelled.session_type == SessionType.cancelled
    assert cancelled.status == ClassSessionStatus.cancelled.value
    assert cancelled.is_open is False
    
def test_admin_can_cancel_any_teachers_session(db_session: Session):
    teacher = User(
        full_name="Session Teacher",
        email="session-teacher@example.com",
        hashed_password="hashed",
        role=UserRole.teacher,
    )

    admin = User(
        full_name="System Admin",
        email="session-admin@example.com",
        hashed_password="hashed",
        role=UserRole.admin,
    )

    db_session.add_all([teacher, admin])
    db_session.commit()

    db_session.refresh(teacher)
    db_session.refresh(admin)

    class_record = Class(
        name="Computer Networks",
        code="CS404",
        department="CSE",
        teacher_id=teacher.id,
    )

    db_session.add(class_record)
    db_session.commit()
    db_session.refresh(class_record)

    session = ClassSession(
        class_id=class_record.id,
        actual_teacher_id=teacher.id,
        date=date.today(),
        start_time=time(12, 0),
        end_time=time(13, 0),
        room="R104",
        session_type=SessionType.regular,
        status=ClassSessionStatus.scheduled.value,
        is_open=False,
    )

    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    cancelled = cancel_session(
        db_session,
        session.id,
        admin,
    )

    assert cancelled.session_type == SessionType.cancelled
    assert cancelled.status == ClassSessionStatus.cancelled.value
    assert cancelled.is_open is False
    
def test_teacher_cannot_open_another_teachers_session(
    db_session: Session
):
    teacher_one = User(
        full_name="Open Teacher One",
        email="open-teacher-one@example.com",
        hashed_password="hashed",
        role=UserRole.teacher,
    )

    teacher_two = User(
        full_name="Open Teacher Two",
        email="open-teacher-two@example.com",
        hashed_password="hashed",
        role=UserRole.teacher,
    )

    db_session.add_all([teacher_one, teacher_two])
    db_session.commit()

    db_session.refresh(teacher_one)
    db_session.refresh(teacher_two)

    class_record = Class(
        name="Computer Architecture",
        code="CS405",
        department="CSE",
        teacher_id=teacher_one.id,
    )

    db_session.add(class_record)
    db_session.commit()
    db_session.refresh(class_record)

    session = ClassSession(
        class_id=class_record.id,
        actual_teacher_id=teacher_one.id,
        date=date.today(),
        start_time=time(10, 0),
        end_time=time(11, 0),
        room="R105",
        session_type=SessionType.regular,
        status=ClassSessionStatus.scheduled.value,
        is_open=False,
    )

    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    with pytest.raises(HTTPException) as exc_info:
        class_session_repository.open_session(
            db_session,
            session.id,
            teacher_two,
        )

    assert exc_info.value.status_code == 403
    
def test_teacher_cannot_close_another_teachers_session(
    db_session: Session
):
    teacher_one = User(
        full_name="Close Teacher One",
        email="close-teacher-one@example.com",
        hashed_password="hashed",
        role=UserRole.teacher,
    )

    teacher_two = User(
        full_name="Close Teacher Two",
        email="close-teacher-two@example.com",
        hashed_password="hashed",
        role=UserRole.teacher,
    )

    db_session.add_all([teacher_one, teacher_two])
    db_session.commit()

    db_session.refresh(teacher_one)
    db_session.refresh(teacher_two)

    class_record = Class(
        name="Software Engineering",
        code="CS406",
        department="CSE",
        teacher_id=teacher_one.id,
    )

    db_session.add(class_record)
    db_session.commit()
    db_session.refresh(class_record)

    session = ClassSession(
        class_id=class_record.id,
        actual_teacher_id=teacher_one.id,
        date=date.today(),
        start_time=time(10, 0),
        end_time=time(11, 0),
        room="R106",
        session_type=SessionType.regular,
        status=ClassSessionStatus.conducted.value,
        is_open=True,
    )

    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    with pytest.raises(HTTPException) as exc_info:
        class_session_repository.close_session(
            db_session,
            session.id,
            teacher_two,
        )

    assert exc_info.value.status_code == 403
    
def test_teacher_can_close_own_session(db_session: Session):
    teacher = User(
        full_name="Teacher One",
        email="teacher-close-own@example.com",
        hashed_password="hashed",
        role=UserRole.teacher,
        is_active=True,
    )
    db_session.add(teacher)
    db_session.commit()
    db_session.refresh(teacher)

    class_obj = Class(
        name="Test Class",
        code="TCLOSEOWN",
        department="ECE",
        teacher_id=teacher.id,
    )
    db_session.add(class_obj)
    db_session.commit()
    db_session.refresh(class_obj)

    session = ClassSession(
        class_id=class_obj.id,
        actual_teacher_id=teacher.id,
        date=date.today(),
        start_time=time(10, 0),
        end_time=time(11, 0),
        session_type=SessionType.regular,
        status=ClassSessionStatus.conducted.value,
        is_open=True,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    closed = class_session_repository.close_session(
        db_session,
        session.id,
        teacher,
    )

    assert closed.is_open is False
    assert closed.status == ClassSessionStatus.conducted.value
    
def test_admin_can_close_any_teachers_session(db_session: Session):
    teacher = User(
        full_name="Teacher Two",
        email="teacher-close-admin@example.com",
        hashed_password="hashed",
        role=UserRole.teacher,
        is_active=True,
    )

    admin = User(
        full_name="Admin",
        email="admin-close-any@example.com",
        hashed_password="hashed",
        role=UserRole.admin,
        is_active=True,
    )

    db_session.add_all([teacher, admin])
    db_session.commit()
    db_session.refresh(teacher)
    db_session.refresh(admin)

    class_obj = Class(
        name="Admin Close Class",
        code="TCLOSEADMIN",
        department="CSE",
        teacher_id=teacher.id,
    )
    db_session.add(class_obj)
    db_session.commit()
    db_session.refresh(class_obj)

    session = ClassSession(
        class_id=class_obj.id,
        actual_teacher_id=teacher.id,
        date=date.today(),
        start_time=time(11, 0),
        end_time=time(12, 0),
        session_type=SessionType.regular,
        status=ClassSessionStatus.conducted.value,
        is_open=True,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    closed = class_session_repository.close_session(
        db_session,
        session.id,
        admin,
    )

    assert closed.is_open is False
    assert closed.status == ClassSessionStatus.conducted.value
    
def test_duplicate_attendance_is_rejected(db_session: Session):
    class_obj = _seed_teacher_and_class(db_session)

    student_user = User(
        full_name="Attendance Student",
        email="attendance-duplicate@example.com",
        hashed_password="hashed",
        role=UserRole.student,
        is_active=True,
    )
    db_session.add(student_user)
    db_session.commit()
    db_session.refresh(student_user)

    student = Student(
        user_id=student_user.id,
        roll_number="DUP001",
        department="ECE",
        semester=5,
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)

    session = ClassSession(
        class_id=class_obj.id,
        actual_teacher_id=class_obj.teacher_id,
        date=date.today(),
        start_time=time(9, 0),
        end_time=time(10, 0),
        session_type=SessionType.regular,
        status=ClassSessionStatus.conducted.value,
        is_open=True,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    first = attendance_service.mark_attendance(
        db_session,
        student_id=student.id,
        class_session_id=session.id,
        att_status=AttendanceStatus.present,
    )

    assert first.student_id == student.id
    assert first.class_session_id == session.id

    with pytest.raises(HTTPException) as exc_info:
        attendance_service.mark_attendance(
            db_session,
            student_id=student.id,
            class_session_id=session.id,
            att_status=AttendanceStatus.present,
        )

    assert exc_info.value.status_code == 409
    
def test_database_rejects_duplicate_attendance_pair(db_session: Session):
    class_obj = _seed_teacher_and_class(db_session)

    student_user = User(
        full_name="Database Attendance Student",
        email="attendance-db-duplicate@example.com",
        hashed_password="hashed",
        role=UserRole.student,
        is_active=True,
    )
    db_session.add(student_user)
    db_session.commit()
    db_session.refresh(student_user)

    student = Student(
        user_id=student_user.id,
        roll_number="DBDUP001",
        department="ECE",
        semester=5,
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)

    session = ClassSession(
        class_id=class_obj.id,
        actual_teacher_id=class_obj.teacher_id,
        date=date.today(),
        start_time=time(10, 0),
        end_time=time(11, 0),
        session_type=SessionType.regular,
        status=ClassSessionStatus.conducted.value,
        is_open=True,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    first = Attendance(
        student_id=student.id,
        class_session_id=session.id,
        status=AttendanceStatus.present,
    )

    db_session.add(first)
    db_session.commit()

    duplicate = Attendance(
        student_id=student.id,
        class_session_id=session.id,
        status=AttendanceStatus.late,
    )

    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()
    
def test_teacher_can_mark_attendance_in_own_open_session(db_session: Session):
    class_obj = _seed_teacher_and_class(db_session)

    student_user = User(
        full_name="Lifecycle Student",
        email="lifecycle-own@example.com",
        hashed_password="hashed",
        role=UserRole.student,
        is_active=True,
    )
    db_session.add(student_user)
    db_session.commit()
    db_session.refresh(student_user)

    student = Student(
        user_id=student_user.id,
        roll_number="LIFE001",
        department="CSE",
        semester=5,
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)

    session = ClassSession(
        class_id=class_obj.id,
        actual_teacher_id=class_obj.teacher_id,
        date=date.today(),
        start_time=time(9, 0),
        end_time=time(10, 0),
        session_type=SessionType.regular,
        status=ClassSessionStatus.conducted.value,
        is_open=True,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    attendance = attendance_service.mark_attendance(
        db_session,
        student_id=student.id,
        class_session_id=session.id,
        att_status=AttendanceStatus.present,
    )

    assert attendance.student_id == student.id
    assert attendance.class_session_id == session.id
    assert attendance.status == AttendanceStatus.present
    
def test_teacher_cannot_mark_attendance_in_another_teachers_session(
    db_session: Session,
):
    class_obj = _seed_teacher_and_class(db_session)

    another_teacher = User(
        full_name="Teacher Two",
        email="teacher2-attendance@example.com",
        hashed_password="hashed",
        role=UserRole.teacher,
        is_active=True,
    )
    db_session.add(another_teacher)
    db_session.commit()
    db_session.refresh(another_teacher)

    student_user = User(
        full_name="Unauthorized Attendance Student",
        email="unauthorized-attendance@example.com",
        hashed_password="hashed",
        role=UserRole.student,
        is_active=True,
    )
    db_session.add(student_user)
    db_session.commit()
    db_session.refresh(student_user)

    student = Student(
        user_id=student_user.id,
        roll_number="LIFE002",
        department="CSE",
        semester=5,
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)

    session = ClassSession(
        class_id=class_obj.id,
        actual_teacher_id=class_obj.teacher_id,
        date=date.today(),
        start_time=time(10, 0),
        end_time=time(11, 0),
        session_type=SessionType.regular,
        status=ClassSessionStatus.conducted.value,
        is_open=True,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    with pytest.raises(HTTPException) as exc_info:
        attendance_service.mark_attendance(
            db_session,
            student_id=student.id,
            class_session_id=session.id,
            att_status=AttendanceStatus.present,
            requesting_user=another_teacher,
        )

    assert exc_info.value.status_code == 403
    
def test_attendance_cannot_be_marked_when_session_is_closed(
    db_session: Session,
):
    class_obj = _seed_teacher_and_class(db_session)

    student_user = User(
        full_name="Closed Session Student",
        email="closed-session-attendance@example.com",
        hashed_password="hashed",
        role=UserRole.student,
        is_active=True,
    )
    db_session.add(student_user)
    db_session.commit()
    db_session.refresh(student_user)

    student = Student(
        user_id=student_user.id,
        roll_number="LIFE003",
        department="CSE",
        semester=5,
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)

    session = ClassSession(
        class_id=class_obj.id,
        actual_teacher_id=class_obj.teacher_id,
        date=date.today(),
        start_time=time(11, 0),
        end_time=time(12, 0),
        session_type=SessionType.regular,
        status=ClassSessionStatus.conducted.value,
        is_open=False,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    with pytest.raises(HTTPException) as exc_info:
        attendance_service.mark_attendance(
            db_session,
            student_id=student.id,
            class_session_id=session.id,
            att_status=AttendanceStatus.present,
        )

    assert exc_info.value.status_code == 400
    
def test_attendance_cannot_be_marked_for_cancelled_session(
    db_session: Session,
):
    class_obj = _seed_teacher_and_class(db_session)

    student_user = User(
        full_name="Cancelled Session Student",
        email="cancelled-session-attendance@example.com",
        hashed_password="hashed",
        role=UserRole.student,
        is_active=True,
    )
    db_session.add(student_user)
    db_session.commit()
    db_session.refresh(student_user)

    student = Student(
        user_id=student_user.id,
        roll_number="LIFE004",
        department="CSE",
        semester=5,
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)

    session = ClassSession(
        class_id=class_obj.id,
        actual_teacher_id=class_obj.teacher_id,
        date=date.today(),
        start_time=time(12, 0),
        end_time=time(13, 0),
        session_type=SessionType.cancelled,
        status=ClassSessionStatus.cancelled.value,
        is_open=False,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    with pytest.raises(HTTPException) as exc_info:
        attendance_service.mark_attendance(
            db_session,
            student_id=student.id,
            class_session_id=session.id,
            att_status=AttendanceStatus.present,
        )

    assert exc_info.value.status_code == 400