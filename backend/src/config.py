import os
from dataclasses import dataclass

@dataclass
class Config:
    # Database
    DB_AUTO_MIGRATE: bool = os.getenv("DB_AUTO_MIGRATE", "1").lower() in {"1", "true", "yes"}

    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))

    # App
    APP_VERSION: str = os.getenv("APP_VERSION", "dev")
    SYSTEM_CONFIG_FILE: str = os.getenv("SYSTEM_CONFIG_FILE", "/data/storage/system_config.json")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "*")

    # AI Providers
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    OPENAI_TIMEOUT: int = int(os.getenv("OPENAI_TIMEOUT", "600"))
    AZURE_OPENAI_API_KEY: str | None = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_ENDPOINT: str | None = os.getenv("AZURE_OPENAI_ENDPOINT")
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11435")

    # Feature Flags
    AI_PROCESSING_ENABLED: bool = os.getenv("AI_PROCESSING_ENABLED", "true").lower() == "true"
    ENABLE_REAL_OCR: bool = os.getenv("ENABLE_REAL_OCR", "true").lower() == "true"

config = Config()
