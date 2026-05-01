from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# The engine is the actual connection to your database file
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}  # needed only for SQLite
)

# SessionLocal is a factory — each request gets its own session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base is the parent class all models will inherit from
Base = declarative_base()

# Dependency — used in routes to get a DB session per request
def get_db():
    db = SessionLocal()
    try:
        yield db        # give the session to the route
    finally:
        db.close()      # always close after the request finishes