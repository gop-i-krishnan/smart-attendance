import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db

from datetime import date, time

from app.models.class_session import SessionType
from app.models.attendance import AttendanceStatus
from app.core.security import hash_password
from app.models.class_ import Class
from app.models.timetable import Timetable
from app.models.user import User, UserRole
from app.services.auth_service import register_user
from app.schemas.user import UserCreate
from app.models.enrollment import Enrollment
from app.models.student import Student


# ---------------------------------------------------------
# Isolated test database
# ---------------------------------------------------------

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=test_engine)

    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------
# Basic API test
# ---------------------------------------------------------

def test_api_application_is_reachable(client):
    response = client.get("/")

    assert response.status_code == 200
    

def test_admin_can_get_timetable(client, db_session):
    # -----------------------------------------------------
    # Create admin
    # -----------------------------------------------------
    admin = User(
        full_name="API Admin",
        email="api-admin@example.com",
        hashed_password=hash_password("admin123"),
        role=UserRole.admin,
        is_active=True,
    )

    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    # -----------------------------------------------------
    # Create timetable
    # -----------------------------------------------------
    teacher = User(
        full_name="API Teacher",
        email="api-teacher@example.com",
        hashed_password=hash_password("teacher123"),
        role=UserRole.teacher,
        is_active=True,
    )

    db_session.add(teacher)
    db_session.commit()
    db_session.refresh(teacher)

    class_obj = Class(
        name="API Test Class",
        code="API101",
        department="CSE",
        teacher_id=teacher.id,
    )

    db_session.add(class_obj)
    db_session.commit()
    db_session.refresh(class_obj)

    timetable = Timetable(
        class_id=class_obj.id,
        day_of_week="Monday",
        start_time=time(9, 0),
        end_time=time(10, 0),
        room="R101",
    )

    db_session.add(timetable)
    db_session.commit()
    db_session.refresh(timetable)

    # -----------------------------------------------------
    # Login
    # -----------------------------------------------------
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "api-admin@example.com",
            "password": "admin123",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    # -----------------------------------------------------
    # Request timetable
    # -----------------------------------------------------
    response = client.get(
        f"/api/v1/timetable/{timetable.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == timetable.id
    assert data["class_id"] == class_obj.id
    assert data["day_of_week"] == "Monday"
    assert data["room"] == "R101"
    
def test_teacher_cannot_get_another_teachers_timetable(client, db_session):
    # -----------------------------------------------------
    # Create two teachers
    # -----------------------------------------------------
    teacher_one = User(
        full_name="Teacher One",
        email="api-teacher-one@example.com",
        hashed_password=hash_password("teacher123"),
        role=UserRole.teacher,
        is_active=True,
    )

    teacher_two = User(
        full_name="Teacher Two",
        email="api-teacher-two@example.com",
        hashed_password=hash_password("teacher123"),
        role=UserRole.teacher,
        is_active=True,
    )

    db_session.add_all([teacher_one, teacher_two])
    db_session.commit()

    db_session.refresh(teacher_one)
    db_session.refresh(teacher_two)

    # -----------------------------------------------------
    # Create class owned by Teacher One
    # -----------------------------------------------------
    class_obj = Class(
        name="Teacher One Class",
        code="API102",
        department="CSE",
        teacher_id=teacher_one.id,
    )

    db_session.add(class_obj)
    db_session.commit()
    db_session.refresh(class_obj)

    # -----------------------------------------------------
    # Create timetable for Teacher One's class
    # -----------------------------------------------------
    timetable = Timetable(
        class_id=class_obj.id,
        day_of_week="Tuesday",
        start_time=time(10, 0),
        end_time=time(11, 0),
        room="R102",
    )

    db_session.add(timetable)
    db_session.commit()
    db_session.refresh(timetable)

    # -----------------------------------------------------
    # Login as Teacher Two
    # -----------------------------------------------------
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "api-teacher-two@example.com",
            "password": "teacher123",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    # -----------------------------------------------------
    # Teacher Two attempts to access Teacher One's timetable
    # -----------------------------------------------------
    response = client.get(
        f"/api/v1/timetable/{timetable.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    # Must be forbidden
    assert response.status_code == 403
    
def test_enrolled_student_can_get_class_timetable(client, db_session):
    # -----------------------------------------------------
    # Create teacher
    # -----------------------------------------------------
    teacher = User(
        full_name="API Teacher",
        email="api-enrollment-teacher@example.com",
        hashed_password=hash_password("teacher123"),
        role=UserRole.teacher,
        is_active=True,
    )

    # -----------------------------------------------------
    # Create student user
    # -----------------------------------------------------
    student_user = User(
        full_name="API Student",
        email="api-student@example.com",
        hashed_password=hash_password("student123"),
        role=UserRole.student,
        is_active=True,
    )

    db_session.add_all([teacher, student_user])
    db_session.commit()

    db_session.refresh(teacher)
    db_session.refresh(student_user)

    # -----------------------------------------------------
    # Create student profile
    # -----------------------------------------------------
    student = Student(
        user_id=student_user.id,
        roll_number="API-STU-001",
        department="CSE",
        semester=5,
    )

    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)

    # -----------------------------------------------------
    # Create class owned by teacher
    # -----------------------------------------------------
    class_obj = Class(
        name="API Enrolled Class",
        code="API103",
        department="CSE",
        teacher_id=teacher.id,
    )

    db_session.add(class_obj)
    db_session.commit()
    db_session.refresh(class_obj)

    # -----------------------------------------------------
    # Enroll student
    # -----------------------------------------------------
    enrollment = Enrollment(
        student_id=student.id,
        class_id=class_obj.id,
        is_active=True,
    )

    db_session.add(enrollment)
    db_session.commit()

    # -----------------------------------------------------
    # Create timetable
    # -----------------------------------------------------
    timetable = Timetable(
        class_id=class_obj.id,
        day_of_week="Wednesday",
        start_time=time(11, 0),
        end_time=time(12, 0),
        room="R103",
    )

    db_session.add(timetable)
    db_session.commit()
    db_session.refresh(timetable)

    # -----------------------------------------------------
    # Login as student
    # -----------------------------------------------------
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "api-student@example.com",
            "password": "student123",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    # -----------------------------------------------------
    # Student accesses timetable
    # -----------------------------------------------------
    response = client.get(
        f"/api/v1/timetable/{timetable.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == timetable.id
    assert data["class_id"] == class_obj.id
    assert data["day_of_week"] == "Wednesday"
    
def test_teacher_to_student_attendance_workflow(client, db_session):
    # ---------------------------------------------------------
    # 1. Create teacher
    # ---------------------------------------------------------
    teacher = User(
        full_name="Workflow Teacher",
        email="workflow-teacher@example.com",
        hashed_password=hash_password("teacher123"),
        role=UserRole.teacher,
        is_active=True,
    )

    # ---------------------------------------------------------
    # 2. Create student user
    # ---------------------------------------------------------
    student_user = User(
        full_name="Workflow Student",
        email="workflow-student@example.com",
        hashed_password=hash_password("student123"),
        role=UserRole.student,
        is_active=True,
    )

    db_session.add_all([teacher, student_user])
    db_session.commit()

    db_session.refresh(teacher)
    db_session.refresh(student_user)

    # ---------------------------------------------------------
    # 3. Create student profile
    # ---------------------------------------------------------
    student = Student(
        user_id=student_user.id,
        roll_number="WORKFLOW-STU-001",
        department="CSE",
        semester=5,
    )

    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)

    # ---------------------------------------------------------
    # 4. Create class assigned to teacher
    # ---------------------------------------------------------
    class_obj = Class(
        name="Workflow Class",
        code="WF101",
        department="CSE",
        teacher_id=teacher.id,
    )

    db_session.add(class_obj)
    db_session.commit()
    db_session.refresh(class_obj)

    # ---------------------------------------------------------
    # 5. Enroll student in class
    # ---------------------------------------------------------
    enrollment = Enrollment(
        student_id=student.id,
        class_id=class_obj.id,
        is_active=True,
    )

    db_session.add(enrollment)
    db_session.commit()

    # ---------------------------------------------------------
    # 6. Create timetable
    # ---------------------------------------------------------
    timetable = Timetable(
        class_id=class_obj.id,
        day_of_week="Monday",
        start_time=time(10, 0),
        end_time=time(11, 0),
        room="WF101",
    )

    db_session.add(timetable)
    db_session.commit()
    db_session.refresh(timetable)

    # ---------------------------------------------------------
    # 7. Teacher login
    # ---------------------------------------------------------
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "workflow-teacher@example.com",
            "password": "teacher123",
        },
    )

    assert login_response.status_code == 200

    teacher_token = login_response.json()["access_token"]

    teacher_headers = {
        "Authorization": f"Bearer {teacher_token}"
    }

    # ---------------------------------------------------------
    # 8. Create class session
    # ---------------------------------------------------------
    session_response = client.post(
        "/api/v1/session/",
        json={
            "class_id": class_obj.id,
            "timetable_id": timetable.id,
            "actual_teacher_id": teacher.id,
            "date": str(date.today()),
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "room": "WF101",
            "session_type": SessionType.regular.value,
        },
        headers=teacher_headers,
    )

    assert session_response.status_code == 200, session_response.text

    session_data = session_response.json()
    session_id = session_data["id"]

    # ---------------------------------------------------------
    # 9. Open the session
    # ---------------------------------------------------------
    open_response = client.post(
        f"/api/v1/session/{session_id}/open",
        headers=teacher_headers,
    )

    assert open_response.status_code == 200, open_response.text
    assert open_response.json()["id"] == session_id

    # ---------------------------------------------------------
    # 10. Mark student attendance
    # ---------------------------------------------------------
    attendance_response = client.post(
        "/api/v1/attendance/mark",
        json={
            "student_id": student.id,
            "class_session_id": session_id,
            "status": AttendanceStatus.present.value,
        },
        headers=teacher_headers,
    )

    assert attendance_response.status_code == 200, attendance_response.text

    attendance_data = attendance_response.json()

    assert attendance_data["student_id"] == student.id
    assert attendance_data["class_session_id"] == session_id
    assert attendance_data["status"] == AttendanceStatus.present.value

    # ---------------------------------------------------------
    # 11. Close the session
    # ---------------------------------------------------------
    close_response = client.post(
        f"/api/v1/session/{session_id}/close",
        headers=teacher_headers,
    )

    assert close_response.status_code == 200, close_response.text
    assert close_response.json()["id"] == session_id

    # ---------------------------------------------------------
    # 12. Student login
    # ---------------------------------------------------------
    student_login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "workflow-student@example.com",
            "password": "student123",
        },
    )

    assert student_login_response.status_code == 200

    student_token = student_login_response.json()["access_token"]

    student_headers = {
        "Authorization": f"Bearer {student_token}"
    }

    # ---------------------------------------------------------
    # 13. Student retrieves attendance
    # ---------------------------------------------------------
    student_attendance_response = client.get(
        f"/api/v1/attendance/student/{student.id}",
        headers=student_headers,
    )

    assert student_attendance_response.status_code == 200

    attendance_records = student_attendance_response.json()

    assert len(attendance_records) == 1
    assert attendance_records[0]["student_id"] == student.id
    assert attendance_records[0]["class_session_id"] == session_id

    # ---------------------------------------------------------
    # 14. Student retrieves attendance summary
    # ---------------------------------------------------------
    summary_response = client.get(
        f"/api/v1/attendance/student/{student.id}/summary",
        headers=student_headers,
    )

    assert summary_response.status_code == 200

    summary = summary_response.json()

    assert summary["student_id"] == student.id
    assert summary["present"] == 1
    assert summary["absent"] == 0
    assert summary["late"] == 0
    
def test_teacher_cannot_mark_attendance_for_unenrolled_student(
    client,
    db_session,
):
    teacher = User(
        full_name="Enrollment Teacher",
        email="unenrolled-teacher@example.com",
        hashed_password=hash_password("teacher123"),
        role=UserRole.teacher,
        is_active=True,
    )

    student_user = User(
        full_name="Unenrolled Student",
        email="unenrolled-student@example.com",
        hashed_password=hash_password("student123"),
        role=UserRole.student,
        is_active=True,
    )

    db_session.add_all([teacher, student_user])
    db_session.commit()

    db_session.refresh(teacher)
    db_session.refresh(student_user)

    student = Student(
        user_id=student_user.id,
        roll_number="UNENROLLED-001",
        department="CSE",
        semester=5,
    )

    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)

    class_obj = Class(
        name="Enrollment Test Class",
        code="ENR101",
        department="CSE",
        teacher_id=teacher.id,
    )

    db_session.add(class_obj)
    db_session.commit()
    db_session.refresh(class_obj)

    # Intentionally NO enrollment is created.

    timetable = Timetable(
        class_id=class_obj.id,
        day_of_week="Tuesday",
        start_time=time(10, 0),
        end_time=time(11, 0),
        room="ENR101",
    )

    db_session.add(timetable)
    db_session.commit()
    db_session.refresh(timetable)

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "unenrolled-teacher@example.com",
            "password": "teacher123",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Create session.
    session_response = client.post(
        "/api/v1/session/",
        json={
            "class_id": class_obj.id,
            "timetable_id": timetable.id,
            "actual_teacher_id": teacher.id,
            "date": str(date.today()),
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "room": "ENR101",
            "session_type": SessionType.regular.value,
        },
        headers=headers,
    )

    assert session_response.status_code == 200, session_response.text

    session_id = session_response.json()["id"]

    # Open session.
    open_response = client.post(
        f"/api/v1/session/{session_id}/open",
        headers=headers,
    )

    assert open_response.status_code == 200, open_response.text

    # Try to mark an unenrolled student.
    attendance_response = client.post(
        "/api/v1/attendance/mark",
        json={
            "student_id": student.id,
            "class_session_id": session_id,
            "status": AttendanceStatus.present.value,
        },
        headers=headers,
    )

    assert attendance_response.status_code == 403
    assert attendance_response.json()["detail"] == (
        "Student is not enrolled in this class"
    )
    
def test_duplicate_attendance_is_rejected(client, db_session):
    teacher = User(
        full_name="Duplicate Teacher",
        email="duplicate-teacher@example.com",
        hashed_password=hash_password("teacher123"),
        role=UserRole.teacher,
        is_active=True,
    )

    student_user = User(
        full_name="Duplicate Student",
        email="duplicate-student@example.com",
        hashed_password=hash_password("student123"),
        role=UserRole.student,
        is_active=True,
    )

    db_session.add_all([teacher, student_user])
    db_session.commit()

    db_session.refresh(teacher)
    db_session.refresh(student_user)

    student = Student(
        user_id=student_user.id,
        roll_number="DUPLICATE-001",
        department="CSE",
        semester=5,
    )

    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)

    class_obj = Class(
        name="Duplicate Attendance Class",
        code="DUP101",
        department="CSE",
        teacher_id=teacher.id,
    )

    db_session.add(class_obj)
    db_session.commit()
    db_session.refresh(class_obj)

    enrollment = Enrollment(
        student_id=student.id,
        class_id=class_obj.id,
        is_active=True,
    )

    db_session.add(enrollment)
    db_session.commit()

    timetable = Timetable(
        class_id=class_obj.id,
        day_of_week="Wednesday",
        start_time=time(10, 0),
        end_time=time(11, 0),
        room="DUP101",
    )

    db_session.add(timetable)
    db_session.commit()
    db_session.refresh(timetable)

    # Teacher login
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "duplicate-teacher@example.com",
            "password": "teacher123",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Create session
    session_response = client.post(
        "/api/v1/session/",
        json={
            "class_id": class_obj.id,
            "timetable_id": timetable.id,
            "actual_teacher_id": teacher.id,
            "date": str(date.today()),
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "room": "DUP101",
            "session_type": SessionType.regular.value,
        },
        headers=headers,
    )

    assert session_response.status_code == 200, session_response.text

    session_id = session_response.json()["id"]

    # Open session
    open_response = client.post(
        f"/api/v1/session/{session_id}/open",
        headers=headers,
    )

    assert open_response.status_code == 200, open_response.text

    # First attendance mark
    first_response = client.post(
        "/api/v1/attendance/mark",
        json={
            "student_id": student.id,
            "class_session_id": session_id,
            "status": AttendanceStatus.present.value,
        },
        headers=headers,
    )

    assert first_response.status_code == 200, first_response.text

    # Second attendance mark for the same student/session
    duplicate_response = client.post(
        "/api/v1/attendance/mark",
        json={
            "student_id": student.id,
            "class_session_id": session_id,
            "status": AttendanceStatus.present.value,
        },
        headers=headers,
    )

    assert duplicate_response.status_code == 409
    
def test_closed_session_rejects_attendance(client, db_session):
    teacher = User(
        full_name="Closed Session Teacher",
        email="closed-session-teacher@example.com",
        hashed_password=hash_password("teacher123"),
        role=UserRole.teacher,
        is_active=True,
    )

    student_user = User(
        full_name="Closed Session Student",
        email="closed-session-student@example.com",
        hashed_password=hash_password("student123"),
        role=UserRole.student,
        is_active=True,
    )

    db_session.add_all([teacher, student_user])
    db_session.commit()

    db_session.refresh(teacher)
    db_session.refresh(student_user)

    student = Student(
        user_id=student_user.id,
        roll_number="CLOSED-001",
        department="CSE",
        semester=5,
    )

    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)

    class_obj = Class(
        name="Closed Session Class",
        code="CLS101",
        department="CSE",
        teacher_id=teacher.id,
    )

    db_session.add(class_obj)
    db_session.commit()
    db_session.refresh(class_obj)

    enrollment = Enrollment(
        student_id=student.id,
        class_id=class_obj.id,
        is_active=True,
    )

    db_session.add(enrollment)
    db_session.commit()

    timetable = Timetable(
        class_id=class_obj.id,
        day_of_week="Thursday",
        start_time=time(10, 0),
        end_time=time(11, 0),
        room="CLS101",
    )

    db_session.add(timetable)
    db_session.commit()
    db_session.refresh(timetable)

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "closed-session-teacher@example.com",
            "password": "teacher123",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    headers = {
        "Authorization": f"Bearer {token}"
    }

    session_response = client.post(
        "/api/v1/session/",
        json={
            "class_id": class_obj.id,
            "timetable_id": timetable.id,
            "actual_teacher_id": teacher.id,
            "date": str(date.today()),
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "room": "CLS101",
            "session_type": SessionType.regular.value,
        },
        headers=headers,
    )

    assert session_response.status_code == 200, session_response.text

    session_id = session_response.json()["id"]

    # Open session.
    open_response = client.post(
        f"/api/v1/session/{session_id}/open",
        headers=headers,
    )

    assert open_response.status_code == 200, open_response.text

    # Close session without marking attendance.
    close_response = client.post(
        f"/api/v1/session/{session_id}/close",
        headers=headers,
    )

    assert close_response.status_code == 200, close_response.text

    # Try to mark attendance after the session is closed.
    attendance_response = client.post(
        "/api/v1/attendance/mark",
        json={
            "student_id": student.id,
            "class_session_id": session_id,
            "status": AttendanceStatus.present.value,
        },
        headers=headers,
    )

    assert attendance_response.status_code == 400
    assert attendance_response.json()["detail"] == (
        "Attendance cannot be marked when the session is closed"
    )
    
def test_admin_can_see_all_classes(client, db_session):
    admin = User(
        full_name="Class Access Admin",
        email="class-access-admin@example.com",
        hashed_password=hash_password("admin123"),
        role=UserRole.admin,
        is_active=True,
    )

    teacher_one = User(
        full_name="Class Access Teacher One",
        email="class-access-teacher-one@example.com",
        hashed_password=hash_password("teacher123"),
        role=UserRole.teacher,
        is_active=True,
    )

    teacher_two = User(
        full_name="Class Access Teacher Two",
        email="class-access-teacher-two@example.com",
        hashed_password=hash_password("teacher123"),
        role=UserRole.teacher,
        is_active=True,
    )

    db_session.add_all([admin, teacher_one, teacher_two])
    db_session.commit()

    db_session.refresh(admin)
    db_session.refresh(teacher_one)
    db_session.refresh(teacher_two)

    class_one = Class(
        name="Admin Access Class One",
        code="CAC101",
        department="CSE",
        teacher_id=teacher_one.id,
    )

    class_two = Class(
        name="Admin Access Class Two",
        code="CAC102",
        department="ECE",
        teacher_id=teacher_two.id,
    )

    db_session.add_all([class_one, class_two])
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "class-access-admin@example.com",
            "password": "admin123",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/classes/",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    class_ids = {item["id"] for item in response.json()}

    assert class_one.id in class_ids
    assert class_two.id in class_ids


def test_teacher_can_see_only_assigned_classes(client, db_session):
    teacher_one = User(
        full_name="Class List Teacher One",
        email="class-list-teacher-one@example.com",
        hashed_password=hash_password("teacher123"),
        role=UserRole.teacher,
        is_active=True,
    )

    teacher_two = User(
        full_name="Class List Teacher Two",
        email="class-list-teacher-two@example.com",
        hashed_password=hash_password("teacher123"),
        role=UserRole.teacher,
        is_active=True,
    )

    db_session.add_all([teacher_one, teacher_two])
    db_session.commit()

    db_session.refresh(teacher_one)
    db_session.refresh(teacher_two)

    own_class = Class(
        name="Teacher One Own Class",
        code="TLC101",
        department="CSE",
        teacher_id=teacher_one.id,
    )

    other_class = Class(
        name="Teacher Two Class",
        code="TLC102",
        department="ECE",
        teacher_id=teacher_two.id,
    )

    db_session.add_all([own_class, other_class])
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "class-list-teacher-one@example.com",
            "password": "teacher123",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/classes/",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    class_ids = {item["id"] for item in response.json()}

    assert own_class.id in class_ids
    assert other_class.id not in class_ids


def test_student_can_see_only_active_enrolled_classes(client, db_session):
    teacher = User(
        full_name="Class List Student Teacher",
        email="class-list-student-teacher@example.com",
        hashed_password=hash_password("teacher123"),
        role=UserRole.teacher,
        is_active=True,
    )

    student_user = User(
        full_name="Class List Student",
        email="class-list-student@example.com",
        hashed_password=hash_password("student123"),
        role=UserRole.student,
        is_active=True,
    )

    db_session.add_all([teacher, student_user])
    db_session.commit()

    db_session.refresh(teacher)
    db_session.refresh(student_user)

    student = Student(
        user_id=student_user.id,
        roll_number="CLASS-LIST-STU-001",
        department="CSE",
        semester=5,
    )

    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)

    enrolled_class = Class(
        name="Student Enrolled Class",
        code="SEC101",
        department="CSE",
        teacher_id=teacher.id,
    )

    inactive_class = Class(
        name="Student Inactive Enrollment Class",
        code="SEC102",
        department="CSE",
        teacher_id=teacher.id,
    )

    not_enrolled_class = Class(
        name="Student Not Enrolled Class",
        code="SEC103",
        department="ECE",
        teacher_id=teacher.id,
    )

    db_session.add_all([
        enrolled_class,
        inactive_class,
        not_enrolled_class,
    ])
    db_session.commit()

    db_session.refresh(enrolled_class)
    db_session.refresh(inactive_class)
    db_session.refresh(not_enrolled_class)

    active_enrollment = Enrollment(
        student_id=student.id,
        class_id=enrolled_class.id,
        is_active=True,
    )

    inactive_enrollment = Enrollment(
        student_id=student.id,
        class_id=inactive_class.id,
        is_active=False,
    )

    db_session.add_all([
        active_enrollment,
        inactive_enrollment,
    ])
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "class-list-student@example.com",
            "password": "student123",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/classes/",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    class_ids = {item["id"] for item in response.json()}

    assert enrolled_class.id in class_ids
    assert inactive_class.id not in class_ids
    assert not_enrolled_class.id not in class_ids
    
def test_enrollment_lifecycle_create_deactivate_reactivate(
    client,
    db_session,
):
    # ---------------------------------------------------------
    # 1. Create admin
    # ---------------------------------------------------------
    admin = User(
        full_name="Enrollment Admin",
        email="enrollment-admin@example.com",
        hashed_password=hash_password("admin123"),
        role=UserRole.admin,
        is_active=True,
    )

    # ---------------------------------------------------------
    # 2. Create teacher
    # ---------------------------------------------------------
    teacher = User(
        full_name="Enrollment Teacher",
        email="enrollment-teacher@example.com",
        hashed_password=hash_password("teacher123"),
        role=UserRole.teacher,
        is_active=True,
    )

    # ---------------------------------------------------------
    # 3. Create student user
    # ---------------------------------------------------------
    student_user = User(
        full_name="Enrollment Student",
        email="enrollment-student@example.com",
        hashed_password=hash_password("student123"),
        role=UserRole.student,
        is_active=True,
    )

    db_session.add_all([
        admin,
        teacher,
        student_user,
    ])
    db_session.commit()

    db_session.refresh(admin)
    db_session.refresh(teacher)
    db_session.refresh(student_user)

    # ---------------------------------------------------------
    # 4. Create student profile
    # ---------------------------------------------------------
    student = Student(
        user_id=student_user.id,
        roll_number="ENROLLMENT-001",
        department="CSE",
        semester=5,
    )

    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)

    # ---------------------------------------------------------
    # 5. Create class
    # ---------------------------------------------------------
    class_obj = Class(
        name="Enrollment Lifecycle Class",
        code="ELC101",
        department="CSE",
        teacher_id=teacher.id,
    )

    db_session.add(class_obj)
    db_session.commit()
    db_session.refresh(class_obj)

    # ---------------------------------------------------------
    # 6. Admin login
    # ---------------------------------------------------------
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "enrollment-admin@example.com",
            "password": "admin123",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    headers = {
        "Authorization": f"Bearer {token}"
    }

    # ---------------------------------------------------------
    # 7. Create enrollment
    # ---------------------------------------------------------
    create_response = client.post(
        "/api/v1/enrollments/",
        json={
            "student_id": student.id,
            "class_id": class_obj.id,
        },
        headers=headers,
    )

    assert create_response.status_code == 200

    enrollment_data = create_response.json()

    enrollment_id = enrollment_data["id"]

    assert enrollment_data["student_id"] == student.id
    assert enrollment_data["class_id"] == class_obj.id
    assert enrollment_data["is_active"] is True

    # ---------------------------------------------------------
    # 8. Duplicate active enrollment must be rejected
    # ---------------------------------------------------------
    duplicate_response = client.post(
        "/api/v1/enrollments/",
        json={
            "student_id": student.id,
            "class_id": class_obj.id,
        },
        headers=headers,
    )

    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["detail"] == (
        "Student is already enrolled in this class"
    )

    # ---------------------------------------------------------
    # 9. Deactivate enrollment
    # ---------------------------------------------------------
    deactivate_response = client.delete(
        f"/api/v1/enrollments/{enrollment_id}",
        headers=headers,
    )

    assert deactivate_response.status_code == 200

    deactivated_data = deactivate_response.json()

    assert deactivated_data["id"] == enrollment_id
    assert deactivated_data["is_active"] is False

    # ---------------------------------------------------------
    # 10. Reactivate the same enrollment
    # ---------------------------------------------------------
    reactivate_response = client.post(
        "/api/v1/enrollments/",
        json={
            "student_id": student.id,
            "class_id": class_obj.id,
        },
        headers=headers,
    )

    assert reactivate_response.status_code == 200

    reactivated_data = reactivate_response.json()

    assert reactivated_data["id"] == enrollment_id
    assert reactivated_data["student_id"] == student.id
    assert reactivated_data["class_id"] == class_obj.id
    assert reactivated_data["is_active"] is True
    
def test_non_admin_cannot_create_enrollment(client, db_session):
    teacher = User(
        full_name="Enrollment Auth Teacher",
        email="enrollment-auth-teacher@example.com",
        hashed_password=hash_password("teacher123"),
        role=UserRole.teacher,
        is_active=True,
    )

    student_user = User(
        full_name="Enrollment Auth Student",
        email="enrollment-auth-student@example.com",
        hashed_password=hash_password("student123"),
        role=UserRole.student,
        is_active=True,
    )

    db_session.add_all([teacher, student_user])
    db_session.commit()

    db_session.refresh(teacher)
    db_session.refresh(student_user)

    student = Student(
        user_id=student_user.id,
        roll_number="ENROLL-AUTH-001",
        department="CSE",
        semester=5,
    )

    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)

    class_obj = Class(
        name="Enrollment Auth Class",
        code="EAC101",
        department="CSE",
        teacher_id=teacher.id,
    )

    db_session.add(class_obj)
    db_session.commit()
    db_session.refresh(class_obj)

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "enrollment-auth-teacher@example.com",
            "password": "teacher123",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/enrollments/",
        json={
            "student_id": student.id,
            "class_id": class_obj.id,
        },
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 403
    
def test_non_admin_cannot_deactivate_enrollment(client, db_session):
    teacher = User(
        full_name="Enrollment Deactivate Teacher",
        email="enrollment-deactivate-teacher@example.com",
        hashed_password=hash_password("teacher123"),
        role=UserRole.teacher,
        is_active=True,
    )

    student_user = User(
        full_name="Enrollment Deactivate Student",
        email="enrollment-deactivate-student@example.com",
        hashed_password=hash_password("student123"),
        role=UserRole.student,
        is_active=True,
    )

    db_session.add_all([teacher, student_user])
    db_session.commit()

    db_session.refresh(teacher)
    db_session.refresh(student_user)

    student = Student(
        user_id=student_user.id,
        roll_number="ENROLL-DEACT-001",
        department="CSE",
        semester=5,
    )

    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)

    class_obj = Class(
        name="Enrollment Deactivate Class",
        code="EDC101",
        department="CSE",
        teacher_id=teacher.id,
    )

    db_session.add(class_obj)
    db_session.commit()
    db_session.refresh(class_obj)

    enrollment = Enrollment(
        student_id=student.id,
        class_id=class_obj.id,
        is_active=True,
    )

    db_session.add(enrollment)
    db_session.commit()
    db_session.refresh(enrollment)

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "enrollment-deactivate-teacher@example.com",
            "password": "teacher123",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.delete(
        f"/api/v1/enrollments/{enrollment.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 403