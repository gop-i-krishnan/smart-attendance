from sqlalchemy.orm import Session
from app.models.class_ import Class

def get_class_by_id(db: Session, class_id: int):
    return db.query(Class).filter(Class.id == class_id).first()

def get_all_classes(db: Session):
    return db.query(Class).all()

def create_class(db: Session, name: str, code: str,
                 department: str, teacher_id: int):
    class_ = Class(
        name=name,
        code=code,
        department=department,
        teacher_id=teacher_id
    )
    db.add(class_)
    db.commit()
    db.refresh(class_)
    return class_