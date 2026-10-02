from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.models.class_ import Class
from app.models.notice import Notice
from app.models.student import Student
from app.services.analytics_service import get_all_risk_report, get_detailed_student_analytics


def _as_role_name(role: Any) -> str:
    return role.value if hasattr(role, "value") else str(role)


def build_ai_assistant_summary(db: Session, role: str, user_id: int) -> Dict[str, Any]:
    role_name = _as_role_name(role).lower()
    risk_report = get_all_risk_report(db)
    student_count = len(risk_report)
    class_count = db.query(Class).count()
    notice_count = db.query(Notice).filter(Notice.is_active == True).count()
    danger_count = sum(1 for student in risk_report if student["risk"] == "danger")
    warning_count = sum(1 for student in risk_report if student["risk"] == "warning")
    attendance_details: Dict[str, Any] = {}

    if role_name == "admin":
        header = "Admin AI Assistant"
        summary = (
            f"There are {student_count} student profiles across {class_count} course offerings and {notice_count} active notices. "
            f"Attendance analysis flags {danger_count} students below 75% and {warning_count} in the warning band. "
            "Prioritize outreach and check upcoming calendar events."
        )
        priorities = [
            f"Review the {danger_count} students below the attendance threshold and plan outreach.",
            "Check the academic calendar for events that overlap with classes.",
            "Publish timely notices to keep students informed.",
        ]
    elif role_name == "teacher":
        header = "Teacher AI Assistant"
        assigned_classes = db.query(Class).filter(Class.teacher_id == user_id).count()
        summary = (
            f"Your timetable has {assigned_classes} assigned course offerings. Across {student_count} student profiles, "
            f"{danger_count} are below 75% and {warning_count} are near the threshold. "
            "Review your upcoming sessions and prioritize timely attendance follow-up."
        )
        priorities = [
            "Mark attendance before the end of the day to keep data current.",
            f"Follow up with students below 75% before the next class ({danger_count} currently flagged).",
            "Share updated notices with the class when schedules or exams change.",
        ]
    else:
        header = "Student AI Assistant"
        profile = db.query(Student).filter(Student.user_id == user_id).first()
        if profile:
            attendance_details = get_detailed_student_analytics(db, profile.id)
            percentage = attendance_details["percentage"]
            risk = attendance_details["risk"]
            if risk == "danger":
                summary = (
                    f"Your attendance is {percentage:.0f}% across {attendance_details['total_classes']} sessions. "
                    f"Attend the next {attendance_details['classes_to_recover']} consecutive classes to reach 75%."
                )
                attendance_action = f"Attend the next {attendance_details['classes_to_recover']} classes consecutively to recover above 75%."
            elif risk == "warning":
                summary = (
                    f"Your attendance is {percentage:.0f}% across {attendance_details['total_classes']} sessions. "
                    f"You can miss {attendance_details['classes_can_miss']} more classes and remain above 75%."
                )
                attendance_action = "Keep attending consistently to move your attendance above the safe threshold."
            else:
                summary = (
                    f"Your attendance is {percentage:.0f}% across {attendance_details['total_classes']} sessions. "
                    f"You can miss {attendance_details['classes_can_miss']} more classes and remain above 75%."
                )
                attendance_action = "Maintain your attendance trend and check the schedule before planned absences."
            priorities = [
                attendance_action,
                "Review the academic calendar before long absences.",
                "Use the leave workflow when you need to report an absence.",
            ]
        else:
            summary = f"Your account has no linked student profile yet. There are {notice_count} active notices to review."
            priorities = [
                "Ask the academic office to link your account to a student profile.",
                "Review the academic calendar and current notices.",
                "Use the leave workflow when you need to report an absence.",
            ]

    return {
        "header": header,
        "summary": summary,
        "priority_actions": priorities,
        "student_count": student_count,
        "class_count": class_count,
        "notice_count": notice_count,
        "danger_count": danger_count,
        "warning_count": warning_count,
        "user_id": user_id,
        **({
            "attendance_percentage": attendance_details["percentage"],
            "risk": attendance_details["risk"],
            "classes_to_recover": attendance_details["classes_to_recover"],
            "classes_can_miss": attendance_details["classes_can_miss"],
        } if attendance_details else {}),
    }