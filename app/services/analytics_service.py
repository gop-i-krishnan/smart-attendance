"""
Analytics Service — Shortage detection, risk prediction, what-if analysis.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from app.models.attendance import Attendance, AttendanceStatus
from app.models.class_session import ClassSession, SessionType
from app.models.student import Student
from app.repositories import student_repository

REQUIRED_PERCENTAGE = 75.0


def get_detailed_student_analytics(db: Session, student_id: int) -> Dict[str, Any]:
    """
    Computes comprehensive attendance analytics for a single student:
    - Summary (present/absent/late/percentage)
    - Risk level (safe/warning/danger)
    - Classes needed to recover to 75%
    - Max classes can miss while staying at 75%
    """
    records = db.query(Attendance).filter(Attendance.student_id == student_id).all()

    total = len(records)
    present = sum(1 for r in records if r.status == AttendanceStatus.present)
    absent  = sum(1 for r in records if r.status == AttendanceStatus.absent)
    late    = sum(1 for r in records if r.status == AttendanceStatus.late)
    attended = present + late
    percentage = round((attended / total) * 100, 2) if total > 0 else 0.0

    # Risk classification
    if percentage >= 85:
        risk = "safe"
    elif percentage >= 75:
        risk = "warning"
    else:
        risk = "danger"

    # How many consecutive classes must be attended to cross 75%?
    classes_to_recover = 0
    if percentage < REQUIRED_PERCENTAGE and total > 0:
        # Solve: (attended + x) / (total + x) >= 0.75
        # attended + x >= 0.75*total + 0.75*x
        # 0.25*x >= 0.75*total - attended
        deficit = 0.75 * total - attended
        if deficit > 0:
            classes_to_recover = int(-(-deficit // 0.25))  # ceiling division

    # How many more classes can be missed and still stay >= 75%?
    classes_can_miss = 0
    if percentage >= REQUIRED_PERCENTAGE:
        # Solve: attended / (total + x) >= 0.75
        # attended >= 0.75*total + 0.75*x
        # x <= (attended - 0.75*total) / 0.75
        buffer = (attended - 0.75 * total) / 0.75
        classes_can_miss = max(0, int(buffer))

    return {
        "student_id": student_id,
        "total_classes": total,
        "present": present,
        "absent": absent,
        "late": late,
        "percentage": percentage,
        "risk": risk,
        "classes_to_recover": classes_to_recover,
        "classes_can_miss": classes_can_miss,
    }


def get_class_analytics(db: Session, class_id: int) -> Dict[str, Any]:
    """Per-session attendance stats for a class (rate per session)."""
    sessions = db.query(ClassSession).filter(
        ClassSession.class_id == class_id,
        ClassSession.session_type != SessionType.cancelled
    ).all()

    if not sessions:
        return {"class_id": class_id, "sessions": 0, "avg_attendance_rate": 0.0, "session_breakdown": []}

    breakdown = []
    total_rate = 0.0
    for s in sessions:
        records = db.query(Attendance).filter(Attendance.class_session_id == s.id).all()
        n = len(records)
        p = sum(1 for r in records if r.status in [AttendanceStatus.present, AttendanceStatus.late])
        rate = round((p / n) * 100, 1) if n > 0 else 0.0
        total_rate += rate
        breakdown.append({
            "session_id": s.id,
            "date": str(s.date),
            "session_type": s.session_type,
            "marked": n,
            "present_rate": rate,
        })

    return {
        "class_id": class_id,
        "sessions": len(sessions),
        "avg_attendance_rate": round(total_rate / len(sessions), 1),
        "session_breakdown": sorted(breakdown, key=lambda x: x["date"]),
    }


def get_all_risk_report(db: Session) -> List[Dict[str, Any]]:
    """Returns analytics for every student, sorted by risk."""
    students = student_repository.get_all_students(db)
    results = []
    for s in students:
        analytic = get_detailed_student_analytics(db, s.id)
        analytic["roll_number"] = s.roll_number
        analytic["department"] = s.department
        analytic["semester"] = s.semester
        results.append(analytic)
    # Sort: danger first, then warning, then safe
    order = {"danger": 0, "warning": 1, "safe": 2}
    results.sort(key=lambda x: (order.get(x["risk"], 3), x["percentage"]))
    return results
