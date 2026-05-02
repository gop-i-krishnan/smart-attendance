from sqlalchemy.orm import Session
from app.models.student import Student

def get_student_by_id(db: Session, student_id: int):
    return db.query(Student).filter(Student.id == student_id).first()

def get_student_by_user_id(db: Session, user_id: int):
    return db.query(Student).filter(Student.user_id == user_id).first()

def get_all_students(db: Session):
    return db.query(Student).all()

def create_student(db: Session, user_id: int, roll_number: str,
                   department: str, semester: int):
    student = Student(
        user_id=user_id,
        roll_number=roll_number,
        department=department,
        semester=semester
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student