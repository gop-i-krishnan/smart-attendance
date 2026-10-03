from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AuditLogCreate(BaseModel):
    user_id: Optional[int] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    ip_address: Optional[str] = None
    remarks: Optional[str] = None

class AuditLogOut(BaseModel):
    id: int
    user_id: Optional[int]
    action: str
    entity_type: Optional[str]
    entity_id: Optional[str]
    ip_address: Optional[str]
    remarks: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True
