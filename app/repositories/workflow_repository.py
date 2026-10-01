from sqlalchemy.orm import Session
from app.models.workflows import LeaveRequest, AttendanceCorrection, WorkflowStatus
from app.schemas.workflows import LeaveRequestCreate, AttendanceCorrectionCreate

def create_leave_request(db: Session, student_id: int, data: LeaveRequestCreate):
    record = LeaveRequest(
        student_id=student_id,
        leave_type=data.leave_type,
        from_date=data.from_date,
        to_date=data.to_date,
        reason=data.reason
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

def update_leave_status(db: Session, leave_id: int, status: WorkflowStatus, teacher_id: int):
    record = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if record:
        record.status = status
        record.approved_by = teacher_id
        db.commit()
        db.refresh(record)
    return record

def create_attendance_correction(db: Session, student_id: int, data: AttendanceCorrectionCreate):
    record = AttendanceCorrection(
        student_id=student_id,
        class_session_id=data.class_session_id,
        reason=data.reason
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

def update_correction_status(db: Session, correction_id: int, status: WorkflowStatus, teacher_id: int):
    record = db.query(AttendanceCorrection).filter(AttendanceCorrection.id == correction_id).first()
    if record:
        record.status = status
        record.approved_by = teacher_id
        db.commit()
        db.refresh(record)
    return record
