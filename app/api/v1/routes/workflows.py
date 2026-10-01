from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_teacher
from app.schemas.workflows import LeaveRequestCreate, LeaveRequestOut, AttendanceCorrectionCreate, AttendanceCorrectionOut
from app.models.workflows import WorkflowStatus
from app.repositories import workflow_repository

router = APIRouter()

@router.post("/leave", response_model=LeaveRequestOut)
def request_leave(
    data: LeaveRequestCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if not current_user.student:
        raise HTTPException(status_code=400, detail="Only students can request leave")
    return workflow_repository.create_leave_request(db, current_user.student.id, data)

@router.put("/leave/{leave_id}/status", response_model=LeaveRequestOut)
def update_leave(
    leave_id: int,
    status: WorkflowStatus,
    db: Session = Depends(get_db),
    current_user=Depends(require_teacher)
):
    return workflow_repository.update_leave_status(db, leave_id, status, current_user.id)

@router.post("/correction", response_model=AttendanceCorrectionOut)
def request_correction(
    data: AttendanceCorrectionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if not current_user.student:
        raise HTTPException(status_code=400, detail="Only students can request correction")
    return workflow_repository.create_attendance_correction(db, current_user.student.id, data)

@router.put("/correction/{correction_id}/status", response_model=AttendanceCorrectionOut)
def update_correction(
    correction_id: int,
    status: WorkflowStatus,
    db: Session = Depends(get_db),
    current_user=Depends(require_teacher)
):
    # When a correction is approved, the service layer should probably update the actual attendance record too.
    return workflow_repository.update_correction_status(db, correction_id, status, current_user.id)
