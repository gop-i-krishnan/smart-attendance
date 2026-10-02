from datetime import date, time, timedelta

from app.core.database import Base, SessionLocal, engine
import app.models
from app.core.security import hash_password
from app.models.academic_event import AcademicEvent, EventType
from app.models.attendance import Attendance, AttendanceStatus
from app.models.class_ import Class
from app.models.class_session import ClassSession, SessionType
from app.models.notice import Notice
from app.models.student import Student
from app.models.timetable import Timetable
from app.models.user import User, UserRole

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
PERIODS = (
    (time(8, 30), time(9, 30)),
    (time(9, 30), time(10, 30)),
    (time(10, 45), time(11, 45)),
    (time(11, 45), time(12, 45)),
    (time(13, 30), time(14, 30)),
    (time(14, 30), time(15, 30)),
    (time(15, 30), time(16, 30)),
)

COURSE_DEFINITIONS = (
    ("CS301", "Programming (T-CSE-01)", "CSE", "teacher@rset.edu", "CSE-201"),
    ("CS302", "Database Systems (T-CSE-02)", "CSE", "teacher2@rset.edu", "CSE-202"),
    ("CS303", "Project / Lab (T-CSE-01)", "CSE", "teacher@rset.edu", "CSE-LAB"),
    ("CS304", "Project / Lab (T-CSE-02)", "CSE", "teacher2@rset.edu", "CSE-LAB"),
    ("CS305", "Tutorial (T-CSE-01)", "CSE", "teacher@rset.edu", "CSE-201"),
    ("CS306", "Tutorial (T-CSE-02)", "CSE", "teacher2@rset.edu", "CSE-202"),
    ("EC301", "Digital Electronics (T-ECE-01)", "ECE", "teacher3@rset.edu", "ECE-201"),
    ("EC302", "Communication Systems (T-ECE-02)", "ECE", "teacher4@rset.edu", "ECE-202"),
    ("EC303", "Project / Lab (T-ECE-01)", "ECE", "teacher3@rset.edu", "ECE-LAB"),
    ("EC304", "Project / Lab (T-ECE-02)", "ECE", "teacher4@rset.edu", "ECE-LAB"),
    ("EC305", "Tutorial (T-ECE-01)", "ECE", "teacher3@rset.edu", "ECE-201"),
    ("EC306", "Tutorial (T-ECE-02)", "ECE", "teacher4@rset.edu", "ECE-202"),
)

FIXED_WEEKLY_PLAN = {
    "ECE": (
        ("ece_digital_01", "ece_communication_02", "ece_digital_01", "ece_communication_02", "ece_lab_01", "ece_lab_02", "ece_tutorial_01"),
        ("ece_communication_02", "ece_digital_01", "ece_lab_02", "ece_digital_01", "ece_communication_02", "ece_tutorial_01", "ece_lab_02"),
        ("ece_digital_01", "ece_communication_02", "ece_communication_02", "ece_lab_01", "ece_digital_01", "ece_lab_02", "ece_tutorial_01"),
        ("ece_communication_02", "ece_digital_01", "ece_digital_01", "ece_communication_02", "ece_lab_02", "ece_tutorial_01", "ece_lab_02"),
        ("ece_digital_01", "ece_lab_02", "ece_communication_02", "ece_digital_01", "ece_communication_02", "ece_lab_01", "ece_tutorial_02"),
    ),
    "CSE": (
        ("cse_programming_01", "cse_database_02", "cse_programming_01", "cse_database_02", "cse_lab_01", "cse_lab_02", "cse_tutorial_01"),
        ("cse_database_02", "cse_programming_01", "cse_lab_02", "cse_programming_01", "cse_database_02", "cse_tutorial_01", "cse_lab_02"),
        ("cse_programming_01", "cse_database_02", "cse_database_02", "cse_lab_01", "cse_programming_01", "cse_lab_02", "cse_tutorial_01"),
        ("cse_database_02", "cse_programming_01", "cse_programming_01", "cse_database_02", "cse_lab_02", "cse_tutorial_01", "cse_lab_02"),
        ("cse_programming_01", "cse_lab_02", "cse_database_02", "cse_programming_01", "cse_database_02", "cse_lab_01", "cse_tutorial_02"),
    ),
}

COURSE_KEY_TO_CODE = {
    "cse_programming_01": "CS301",
    "cse_database_02": "CS302",
    "cse_lab_01": "CS303",
    "cse_lab_02": "CS304",
    "cse_tutorial_01": "CS305",
    "cse_tutorial_02": "CS306",
    "ece_digital_01": "EC301",
    "ece_communication_02": "EC302",
    "ece_lab_01": "EC303",
    "ece_lab_02": "EC304",
    "ece_tutorial_01": "EC305",
    "ece_tutorial_02": "EC306",
}


def seed_demo_data() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        demo_users = [
            ("Admin User", "admin@rset.edu", UserRole.admin),
            ("Joy George", "teacher@rset.edu", UserRole.teacher),
            ("Anjali Nair", "teacher2@rset.edu", UserRole.teacher),
            ("Arun Thomas", "teacher3@rset.edu", UserRole.teacher),
            ("Meera Joseph", "teacher4@rset.edu", UserRole.teacher),
            ("Dominic B Moyalan", "student1@rset.edu", UserRole.student),
            ("Gopikrishnan D", "student2@rset.edu", UserRole.student),
            ("Alice Smith", "alice@rset.edu", UserRole.student),
            ("CSE Student 4", "student3@rset.edu", UserRole.student),
            ("CSE Student 5", "student4@rset.edu", UserRole.student),
            ("ECE Student 1", "ece.student1@rset.edu", UserRole.student),
            ("ECE Student 2", "ece.student2@rset.edu", UserRole.student),
            ("ECE Student 3", "ece.student3@rset.edu", UserRole.student),
            ("ECE Student 4", "ece.student4@rset.edu", UserRole.student),
            ("ECE Student 5", "ece.student5@rset.edu", UserRole.student),
        ]
        users = {}
        for full_name, email, role in demo_users:
            user = db.query(User).filter(User.email == email).first()
            if user is None:
                user = User(
                    full_name=full_name,
                    email=email,
                    hashed_password=hash_password("password"),
                    role=role,
                )
                db.add(user)
                db.flush()
            else:
                user.full_name = full_name
                user.role = role
                user.hashed_password = hash_password("password")
            users[email] = user

        student_details = [
            ("student1@rset.edu", "U2301079", "CSE"),
            ("student2@rset.edu", "U2301098", "CSE"),
            ("alice@rset.edu", "U2301000", "CSE"),
            ("student3@rset.edu", "U2301101", "CSE"),
            ("student4@rset.edu", "U2301102", "CSE"),
            ("ece.student1@rset.edu", "E2301001", "ECE"),
            ("ece.student2@rset.edu", "E2301002", "ECE"),
            ("ece.student3@rset.edu", "E2301003", "ECE"),
            ("ece.student4@rset.edu", "E2301004", "ECE"),
            ("ece.student5@rset.edu", "E2301005", "ECE"),
        ]
        students_by_department = {"CSE": [], "ECE": []}
        for email, roll_number, department in student_details:
            student = db.query(Student).filter(Student.user_id == users[email].id).first()
            if student is None:
                existing_roll = db.query(Student).filter(Student.roll_number == roll_number).first()
                if existing_roll is not None and existing_roll.user_id != users[email].id:
                    raise ValueError(f"Roll number {roll_number} is already assigned to another user")
                student = Student(user_id=users[email].id, roll_number=roll_number, department=department, semester=5)
                db.add(student)
                db.flush()
            else:
                student.roll_number = roll_number
                student.department = department
                student.semester = 5
            students_by_department[department].append(student)

        classes_by_code = {}
        for code, name, department, teacher_email, _ in COURSE_DEFINITIONS:
            class_obj = db.query(Class).filter(Class.code == code).first()
            if class_obj is None:
                class_obj = Class(name=name, code=code, department=department, teacher_id=users[teacher_email].id)
                db.add(class_obj)
                db.flush()
            else:
                class_obj.name = name
                class_obj.department = department
                class_obj.teacher_id = users[teacher_email].id
            classes_by_code[code] = class_obj

        desired_by_class_day = {}
        for department, day_rows in FIXED_WEEKLY_PLAN.items():
            for day_name, period_rows in zip(WEEKDAYS, day_rows):
                for period_index, course_key in enumerate(period_rows):
                    class_code = COURSE_KEY_TO_CODE[course_key]
                    course = next(item for item in COURSE_DEFINITIONS if item[0] == class_code)
                    class_obj = classes_by_code[class_code]
                    start_time, end_time = PERIODS[period_index]
                    desired_by_class_day.setdefault((class_obj.id, day_name), []).append(
                        (start_time, end_time, course[4])
                    )

        fixed_timetables = []
        for (class_id, day_name), planned_periods in desired_by_class_day.items():
            existing = (
                db.query(Timetable)
                .filter(Timetable.class_id == class_id, Timetable.day_of_week == day_name)
                .order_by(Timetable.start_time, Timetable.id)
                .all()
            )
            for period_index, (start_time, end_time, room) in enumerate(planned_periods):
                if period_index < len(existing):
                    timetable = existing[period_index]
                    timetable.start_time = start_time
                    timetable.end_time = end_time
                    timetable.room = room
                else:
                    timetable = Timetable(
                        class_id=class_id,
                        day_of_week=day_name,
                        start_time=start_time,
                        end_time=end_time,
                        room=room,
                    )
                    db.add(timetable)
                    db.flush()
                fixed_timetables.append(timetable)

                for session in db.query(ClassSession).filter(ClassSession.timetable_id == timetable.id).all():
                    session.start_time = start_time
                    session.end_time = end_time
                    session.room = room
                    session.actual_teacher_id = classes_by_code[
                        next(code for code, class_obj in classes_by_code.items() if class_obj.id == class_id)
                    ].teacher_id

        status_patterns = [
            [AttendanceStatus.present] * 9 + [AttendanceStatus.late],
            [AttendanceStatus.present] * 8 + [AttendanceStatus.late, AttendanceStatus.absent],
            [AttendanceStatus.present] * 7 + [AttendanceStatus.late, AttendanceStatus.absent, AttendanceStatus.absent],
            [AttendanceStatus.present] * 6 + [AttendanceStatus.late, AttendanceStatus.absent, AttendanceStatus.absent, AttendanceStatus.absent],
            [AttendanceStatus.present] * 4 + [AttendanceStatus.late] + [AttendanceStatus.absent] * 5,
        ]
        holiday_events = db.query(AcademicEvent).filter(AcademicEvent.event_type == EventType.holiday).all()
        past_dates = []
        cursor = date.today() - timedelta(days=1)
        while len(past_dates) < 20:
            is_holiday = any(event.start_date <= cursor <= event.end_date for event in holiday_events)
            if cursor.strftime("%A") in WEEKDAYS and not is_holiday:
                past_dates.append(cursor)
            cursor -= timedelta(days=1)
        past_dates.reverse()

        department_indexes = {"CSE": 0, "ECE": 0}
        for session_date in past_dates:
            day_timetables = sorted(
                (row for row in fixed_timetables if row.day_of_week == session_date.strftime("%A")),
                key=lambda row: row.start_time,
            )
            for timetable in day_timetables:
                class_obj = classes_by_code[
                    next(code for code, item in classes_by_code.items() if item.id == timetable.class_id)
                ]
                session = (
                    db.query(ClassSession)
                    .filter(ClassSession.timetable_id == timetable.id, ClassSession.date == session_date)
                    .first()
                )
                if session is None:
                    session = ClassSession(
                        class_id=class_obj.id,
                        timetable_id=timetable.id,
                        actual_teacher_id=class_obj.teacher_id,
                        date=session_date,
                        start_time=timetable.start_time,
                        end_time=timetable.end_time,
                        room=timetable.room,
                        session_type=SessionType.regular,
                        status="Conducted",
                        remarks="Synthetic fixed-timetable attendance",
                    )
                    db.add(session)
                    db.flush()
                students = students_by_department[class_obj.department]
                attendance_index = department_indexes[class_obj.department]
                for student_index, student in enumerate(students):
                    record = (
                        db.query(Attendance)
                        .filter(Attendance.student_id == student.id, Attendance.class_session_id == session.id)
                        .first()
                    )
                    if record is None:
                        db.add(
                            Attendance(
                                student_id=student.id,
                                class_session_id=session.id,
                                status=status_patterns[student_index][attendance_index % 10],
                            )
                        )
                department_indexes[class_obj.department] += 1

        admin_id = users["admin@rset.edu"].id
        today = date.today()
        events = [
            ("Upcoming Internal Assessment", EventType.exam, today + timedelta(days=7)),
            ("Institution Activity Day", EventType.other, today + timedelta(days=14)),
            ("Campus Holiday", EventType.holiday, today + timedelta(days=21)),
        ]
        for title, event_type, event_date in events:
            exists = db.query(AcademicEvent).filter(AcademicEvent.title == title).first()
            if exists is None:
                db.add(
                    AcademicEvent(
                        title=title,
                        event_type=event_type,
                        start_date=event_date,
                        end_date=event_date,
                        created_by=admin_id,
                    )
                )

        notices = [
            ("Welcome to the semester", "Check your timetable and keep your student profile up to date.", "Announcement"),
            ("Internal assessment", "Review the academic calendar for the upcoming internal assessment.", "Exam Notice"),
        ]
        for title, message, notice_type in notices:
            exists = db.query(Notice).filter(Notice.title == title).first()
            if exists is None:
                db.add(
                    Notice(
                        title=title,
                        message=message,
                        notice_type=notice_type,
                        created_by=admin_id,
                    )
                )

        db.commit()
        print("Demo data is ready. Existing records were preserved.")
        print(f"Admin accounts: {db.query(User).filter(User.role == UserRole.admin).count()}")
        print(f"Teacher accounts: {db.query(User).filter(User.role == UserRole.teacher).count()}")
        print(f"Student profiles: {db.query(Student).count()}")
        print(f"CSE students: {db.query(Student).filter(Student.department == 'CSE').count()}")
        print(f"ECE students: {db.query(Student).filter(Student.department == 'ECE').count()}")
        print(f"Classes: {db.query(Class).count()}")
        print(f"Fixed timetable entries: {len(fixed_timetables)}")
        print(f"Class sessions: {db.query(ClassSession).count()}")
        print(f"Attendance records: {db.query(Attendance).count()}")
        print(f"Calendar events: {db.query(AcademicEvent).count()}")
        print(f"Notices: {db.query(Notice).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()