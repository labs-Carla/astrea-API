from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "AstroDev Agent API"

    class Config:
        env_file = ".env"

settings = Settings()