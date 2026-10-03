from pydantic import BaseModel

class ClassCreate(BaseModel):
    name: str
    code: str
    department: str
    semester: int | None = None
    section: str | None = None
    teacher_id: int

class ClassOut(BaseModel):
    id: int
    name: str
    code: str
    department: str
    semester: int | None = None
    section: str | None = None
    teacher_id: int

    class Config:
        from_attributes = True