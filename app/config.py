from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "WeatherGPT"
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    UPSTASH_REDIS_URL: str = ""
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    IMD_PUBLIC_KEY_PEM: str = ""
    # Ingestion Worker Settings
    INGESTION_INTERVAL_MINUTES: int = 15
    # Bhashini Indic Voice Settings
    BHASHINI_USER_ID: str = ""
    BHASHINI_API_KEY: str = ""
    BHASHINI_PIPELINE_ID: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# This line instantiates and exports 'settings'
settings = Settings()