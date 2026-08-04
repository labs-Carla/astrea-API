from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "AstroDev Agent API"
    anthropic_api_key: str = ""
    admin_secret: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
