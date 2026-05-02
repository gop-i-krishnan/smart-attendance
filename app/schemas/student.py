from pydantic import BaseModel

class StudentCreate(BaseModel):
    user_id: int
    roll_number: str
    department: str
    semester: int

class StudentOut(BaseModel):
    id: int
    user_id: int
    roll_number: str
    department: str
    semester: int

    class Config:
        from_attributes = True