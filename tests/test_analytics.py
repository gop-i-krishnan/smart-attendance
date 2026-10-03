"""
Analytics endpoint tests — Phase B + Phase C.

Engine isolation: each test gets its own in-memory SQLite engine so that
the module-level override in test_api.py cannot interfere.
The override is set inside every test that uses the HTTP client.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import date, time

from app.main import app
from app.core.database import Base, get_db
from app.models.user import User, UserRole
from app.models.student import Student
from app.models.class_ import Class
from app.models.class_session import ClassSession, SessionType
from app.models.attendance import Attendance, AttendanceStatus
from app.models.enrollment import Enrollment
from app.core.security import hash_password


# ---------------------------------------------------------
# Per-test engine helper — isolates every test completely
# ---------------------------------------------------------

def make_session():
    """Create a fresh isolated in-memory SQLite session factory."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, factory


@pytest.fixture
def db_and_client():
    """
    Yields (db, client) where:
      - db  is a live SQLAlchemy session backed by a fresh in-memory DB
      - client is a TestClient whose get_db override points to that same DB
    Cleans up fully after each test.
    """
    engine, factory = make_session()
    db = factory()

    def override_get_db():
        s = factory()
        try:
            yield s
        finally:
            s.close()

    # Save previous override (set by test_api.py at module level) and restore on teardown
    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        yield db, client
    finally:
        db.close()
        if previous_override is not None:
            app.dependency_overrides[get_db] = previous_override
        else:
            app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _user(db, email, role, name=None):
    u = User(
        full_name=name or f"User {email}",
        email=email,
        hashed_password=hash_password("password"),
        role=role,
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _student(db, user_id, dept, sem, roll):
    s = Student(user_id=user_id, roll_number=roll, department=dept, semester=sem)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _class(db, name, code, dept, sem, teacher_id):
    c = Class(name=name, code=code, department=dept, semester=sem, teacher_id=teacher_id)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _session(db, class_id, teacher_id=None):
    s = ClassSession(
        class_id=class_id,
        actual_teacher_id=teacher_id or 1,  # placeholder; tests set real teacher_id
        date=date.today(),
        start_time=time(10, 0),
        end_time=time(11, 0),
        session_type=SessionType.regular,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _attendance(db, student_id, session_id, status):
    a = Attendance(student_id=student_id, class_session_id=session_id, status=status)
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _login(client, email):
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": "password"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(client, email):
    return {"Authorization": f"Bearer {_login(client, email)}"}


# =============================================================
# CALCULATION TESTS
# =============================================================

class TestCalculations:

    def test_zero_session_student_is_no_data(self, db_and_client):
        """A student with no attendance records must be 'no_data', not 'danger'."""
        db, client = db_and_client

        s_user = _user(db, "s@test.com", UserRole.student)
        st = _student(db, s_user.id, "CSE", 1, "S001")

        h = _auth(client, "s@test.com")
        resp = client.get(f"/api/v1/analytics/student/{st.id}", headers=h)
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_classes"] == 0
        assert data["percentage"] == 0.0
        assert data["risk"] == "no_data"
        assert data["subject_breakdown"] == []

    def test_normal_attendance_percentage(self, db_and_client):
        """4 present + 1 absent out of 5 => 80% => warning."""
        db, client = db_and_client

        teacher = _user(db, "t@test.com", UserRole.teacher)
        s_user  = _user(db, "s@test.com", UserRole.student)
        st = _student(db, s_user.id, "CSE", 1, "S002")
        cls = _class(db, "Math", "M1", "CSE", 1, teacher.id)

        for _ in range(4):
            sess = _session(db, cls.id, teacher.id)
            _attendance(db, st.id, sess.id, AttendanceStatus.present)
        sess_absent = _session(db, cls.id, teacher.id)
        _attendance(db, st.id, sess_absent.id, AttendanceStatus.absent)

        h = _auth(client, "s@test.com")
        resp = client.get(f"/api/v1/analytics/student/{st.id}", headers=h)
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_classes"] == 5
        assert data["present"] == 4
        assert data["absent"] == 1
        assert data["percentage"] == 80.0
        assert data["risk"] == "warning"

    def test_subject_breakdown_present(self, db_and_client):
        """Subject breakdown must contain one entry per class with correct counts."""
        db, client = db_and_client

        teacher = _user(db, "t@test.com", UserRole.teacher)
        s_user  = _user(db, "s@test.com", UserRole.student)
        st = _student(db, s_user.id, "CSE", 1, "S003")
        cls = _class(db, "Physics", "P1", "CSE", 1, teacher.id)

        sess = _session(db, cls.id, teacher.id)
        _attendance(db, st.id, sess.id, AttendanceStatus.present)

        h = _auth(client, "s@test.com")
        resp = client.get(f"/api/v1/analytics/student/{st.id}", headers=h)
        assert resp.status_code == 200
        data = resp.json()

        assert len(data["subject_breakdown"]) == 1
        sb = data["subject_breakdown"][0]
        assert sb["class_id"] == cls.id
        assert sb["class_name"] == "Physics"
        assert sb["total"] == 1
        assert sb["present"] == 1
        assert sb["percentage"] == 100.0
        assert sb["risk"] == "safe"

    def test_shortage_calculation_preserved(self, db_and_client):
        """classes_to_recover must be > 0 when student is below 75%."""
        db, client = db_and_client

        teacher = _user(db, "t@test.com", UserRole.teacher)
        s_user  = _user(db, "s@test.com", UserRole.student)
        st = _student(db, s_user.id, "CSE", 1, "S004")
        cls = _class(db, "Chem", "C1", "CSE", 1, teacher.id)

        # 1 present, 3 absent => 25% => well below 75%
        sess1 = _session(db, cls.id, teacher.id)
        _attendance(db, st.id, sess1.id, AttendanceStatus.present)
        for _ in range(3):
            s = _session(db, cls.id, teacher.id)
            _attendance(db, st.id, s.id, AttendanceStatus.absent)

        h = _auth(client, "s@test.com")
        resp = client.get(f"/api/v1/analytics/student/{st.id}", headers=h)
        data = resp.json()

        assert data["percentage"] == 25.0
        assert data["risk"] == "danger"
        assert data["classes_to_recover"] > 0
        assert data["classes_can_miss"] == 0

    def test_classes_can_miss_when_safe(self, db_and_client):
        """classes_can_miss must be > 0 when student is well above 75%."""
        db, client = db_and_client

        teacher = _user(db, "t@test.com", UserRole.teacher)
        s_user  = _user(db, "s@test.com", UserRole.student)
        st = _student(db, s_user.id, "CSE", 1, "S005")
        cls = _class(db, "Eng", "E1", "CSE", 1, teacher.id)

        # 10 present => 100%
        for _ in range(10):
            sess = _session(db, cls.id, teacher.id)
            _attendance(db, st.id, sess.id, AttendanceStatus.present)

        h = _auth(client, "s@test.com")
        resp = client.get(f"/api/v1/analytics/student/{st.id}", headers=h)
        data = resp.json()

        assert data["percentage"] == 100.0
        assert data["risk"] == "safe"
        assert data["classes_can_miss"] > 0
        assert data["classes_to_recover"] == 0


# =============================================================
# AUTHORIZATION TESTS
# =============================================================

class TestAuthorization:

    def test_admin_can_access_risk_all(self, db_and_client):
        db, client = db_and_client
        _user(db, "admin@test.com", UserRole.admin)
        h = _auth(client, "admin@test.com")
        resp = client.get("/api/v1/analytics/risk/all", headers=h)
        assert resp.status_code == 200

    def test_teacher_can_access_risk_all_own_students(self, db_and_client):
        """Teacher sees only students from their own classes (via implicit matching)."""
        db, client = db_and_client

        t1 = _user(db, "t1@test.com", UserRole.teacher)
        s_user = _user(db, "s@test.com", UserRole.student)
        st = _student(db, s_user.id, "CSE", 1, "S010")
        _class(db, "DS", "DS1", "CSE", 1, t1.id)

        h = _auth(client, "t1@test.com")
        resp = client.get("/api/v1/analytics/risk/all", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        ids = [r["student_id"] for r in data]
        assert st.id in ids

    def test_teacher_cannot_see_other_dept_students_in_risk_all(self, db_and_client):
        """Teacher with no ECE class cannot see ECE students in risk/all."""
        db, client = db_and_client

        t1 = _user(db, "t1@test.com", UserRole.teacher)
        t2 = _user(db, "t2@test.com", UserRole.teacher)
        s_ece = _user(db, "s@test.com", UserRole.student)
        st_ece = _student(db, s_ece.id, "ECE", 1, "E001")
        # t1 only has a CSE class; t2 has an ECE class
        _class(db, "DS", "DS1", "CSE", 1, t1.id)
        _class(db, "Signals", "SG1", "ECE", 1, t2.id)

        h_t1 = _auth(client, "t1@test.com")
        resp = client.get("/api/v1/analytics/risk/all", headers=h_t1)
        assert resp.status_code == 200
        ids = [r["student_id"] for r in resp.json()]
        assert st_ece.id not in ids

    def test_student_cannot_access_risk_all(self, db_and_client):
        db, client = db_and_client
        s_user = _user(db, "s@test.com", UserRole.student)
        _student(db, s_user.id, "CSE", 1, "S011")
        h = _auth(client, "s@test.com")
        resp = client.get("/api/v1/analytics/risk/all", headers=h)
        assert resp.status_code == 403

    def test_teacher_can_access_own_class_analytics(self, db_and_client):
        db, client = db_and_client
        t1 = _user(db, "t1@test.com", UserRole.teacher)
        cls = _class(db, "OS", "OS1", "CSE", 1, t1.id)

        h = _auth(client, "t1@test.com")
        resp = client.get(f"/api/v1/analytics/class/{cls.id}", headers=h)
        assert resp.status_code == 200

    def test_teacher_cannot_access_other_teachers_class_analytics(self, db_and_client):
        db, client = db_and_client
        t1 = _user(db, "t1@test.com", UserRole.teacher)
        t2 = _user(db, "t2@test.com", UserRole.teacher)
        cls = _class(db, "OS", "OS1", "CSE", 1, t1.id)

        h_t2 = _auth(client, "t2@test.com")
        resp = client.get(f"/api/v1/analytics/class/{cls.id}", headers=h_t2)
        assert resp.status_code == 403

    def test_admin_can_access_any_class_analytics(self, db_and_client):
        db, client = db_and_client
        admin = _user(db, "admin@test.com", UserRole.admin)
        teacher = _user(db, "t@test.com", UserRole.teacher)
        cls = _class(db, "AI", "AI1", "CSE", 1, teacher.id)

        h = _auth(client, "admin@test.com")
        resp = client.get(f"/api/v1/analytics/class/{cls.id}", headers=h)
        assert resp.status_code == 200

    def test_student_can_access_own_analytics(self, db_and_client):
        db, client = db_and_client
        s_user = _user(db, "s@test.com", UserRole.student)
        st = _student(db, s_user.id, "CSE", 1, "S012")

        h = _auth(client, "s@test.com")
        resp = client.get(f"/api/v1/analytics/student/{st.id}", headers=h)
        assert resp.status_code == 200

    def test_student_cannot_access_another_students_analytics(self, db_and_client):
        db, client = db_and_client
        s1 = _user(db, "s1@test.com", UserRole.student)
        s2 = _user(db, "s2@test.com", UserRole.student)
        _student(db, s1.id, "CSE", 1, "S013")
        st2 = _student(db, s2.id, "CSE", 1, "S014")

        h_s1 = _auth(client, "s1@test.com")
        resp = client.get(f"/api/v1/analytics/student/{st2.id}", headers=h_s1)
        assert resp.status_code == 403


# =============================================================
# ADMIN AGGREGATION TESTS
# =============================================================

class TestAdminAggregations:

    def test_admin_overview_structure(self, db_and_client):
        db, client = db_and_client
        _user(db, "admin@test.com", UserRole.admin)
        h = _auth(client, "admin@test.com")

        resp = client.get("/api/v1/analytics/overview", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_students" in data
        assert "total_sessions" in data
        assert "total_attendance_records" in data
        assert "present_count" in data
        assert "absent_count" in data
        assert "overall_percentage" in data

    def test_admin_overview_zero_attendance(self, db_and_client):
        """With no attendance records, percentage must be 0.0 not a division error."""
        db, client = db_and_client
        _user(db, "admin@test.com", UserRole.admin)
        h = _auth(client, "admin@test.com")

        resp = client.get("/api/v1/analytics/overview", headers=h)
        assert resp.status_code == 200
        assert resp.json()["overall_percentage"] == 0.0

    def test_admin_overview_correct_counts(self, db_and_client):
        db, client = db_and_client
        admin   = _user(db, "admin@test.com", UserRole.admin)
        teacher = _user(db, "t@test.com", UserRole.teacher)
        s_user  = _user(db, "s@test.com", UserRole.student)
        st = _student(db, s_user.id, "CSE", 1, "S020")
        cls = _class(db, "Algo", "AG1", "CSE", 1, teacher.id)
        sess = _session(db, cls.id, teacher.id)
        _attendance(db, st.id, sess.id, AttendanceStatus.present)

        h = _auth(client, "admin@test.com")
        resp = client.get("/api/v1/analytics/overview", headers=h)
        data = resp.json()
        assert data["total_students"] >= 1
        assert data["present_count"] == 1
        assert data["overall_percentage"] == 100.0

    def test_admin_department_analytics(self, db_and_client):
        db, client = db_and_client
        admin   = _user(db, "admin@test.com", UserRole.admin)
        teacher = _user(db, "t@test.com", UserRole.teacher)
        s_user  = _user(db, "s@test.com", UserRole.student)
        st = _student(db, s_user.id, "ECE", 1, "E020")
        cls = _class(db, "Circuits", "CR1", "ECE", 1, teacher.id)
        sess = _session(db, cls.id, teacher.id)
        _attendance(db, st.id, sess.id, AttendanceStatus.present)

        h = _auth(client, "admin@test.com")
        resp = client.get("/api/v1/analytics/department", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        depts = [r["department"] for r in data]
        assert "ECE" in depts

    def test_non_admin_cannot_access_overview(self, db_and_client):
        db, client = db_and_client
        s_user = _user(db, "s@test.com", UserRole.student)
        _student(db, s_user.id, "CSE", 1, "S021")

        h = _auth(client, "s@test.com")
        resp = client.get("/api/v1/analytics/overview", headers=h)
        assert resp.status_code == 403

    def test_teacher_cannot_access_department_analytics(self, db_and_client):
        db, client = db_and_client
        _user(db, "t@test.com", UserRole.teacher)

        h = _auth(client, "t@test.com")
        resp = client.get("/api/v1/analytics/department", headers=h)
        assert resp.status_code == 403
