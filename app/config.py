from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Smart Attendance Platform"
    debug: bool = False
    database_url: str = "sqlite:///./attendance.db"
    secret_key: str = "changethis"

    class Config:
        env_file = ".env"

# One shared instance used across the whole app
settings = Settings()