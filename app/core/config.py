from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    PROJECT_NAME: str
    DATABASE_URL: str
    SYNC_DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # SMTP
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str
    SMTP_FROM: str

    BASE_URL: str

    # IA Configuration
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    WHISPER_MODEL_SIZE: str = "base"
    USE_REAL_AI: bool = True

    # Firebase Cloud Messaging (API v1)
    FCM_CREDENTIALS_PATH: str | None = None  # Ruta al archivo JSON de credenciales
    FIREBASE_PROJECT_ID: str | None = None   # ID del proyecto Firebase

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings():
    return Settings()

settings = get_settings()
