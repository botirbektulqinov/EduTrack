"""
EduTrack application settings loaded from environment variables and .env.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "EduTrack"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    ENABLE_API_DOCS: bool = True
    SECRET_KEY: str = "dev-secret-key-change-me"
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"
    API_V1_PREFIX: str = "/api/v1"

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "edu_track"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/edu_track"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/edu_track"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET_KEY: str = "dev-jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_TLS: bool = True
    SMTP_TIMEOUT_SECONDS: int = 20
    MAIL_FROM: str = "noreply@university.edu"
    MAIL_FROM_NAME: str = "EduTrack"

    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "edutrack-media"

    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    DEFAULT_MAX_VIOLATIONS: int = 3
    DEFAULT_TIME_PENALTY_MINUTES: int = 2

    SANDBOX_DOCKER_HOST: str = "unix:///var/run/docker.sock"
    SANDBOX_TIMEOUT_SECONDS: int = 30
    SANDBOX_MEMORY_LIMIT_MB: int = 256

    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 60
    PASSWORD_RESET_URL_PATH: str = "/reset-password"
    ALLOW_PASSWORD_RESET_SIGNED_FALLBACK: bool = False

    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 10
    RATE_LIMIT_REFRESH_PER_MINUTE: int = 20
    RATE_LIMIT_FORGOT_PASSWORD_PER_HOUR: int = 5
    RATE_LIMIT_RESET_PASSWORD_PER_HOUR: int = 10
    RATE_LIMIT_ASSESSMENT_START_PER_MINUTE: int = 5
    RATE_LIMIT_ANSWER_SAVE_PER_MINUTE: int = 60
    RATE_LIMIT_CODE_PREVIEW_PER_MINUTE: int = 5
    RATE_LIMIT_WS_VIOLATION_PER_MINUTE: int = 30

    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return [str(origin).strip() for origin in parsed]
            except json.JSONDecodeError:
                return [origin.strip() for origin in value.split(",") if origin.strip()]
        return list(value)

    @field_validator("DEBUG", "ENABLE_API_DOCS", "SMTP_TLS", "RATE_LIMIT_ENABLED", "ALLOW_PASSWORD_RESET_SIGNED_FALLBACK", mode="before")
    @classmethod
    def parse_bool_flag(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on", "debug", "development", "dev"}:
                return True
            if normalized in {"false", "0", "no", "off", "release", "production", "prod"}:
                return False
        raise ValueError("Boolean settings must use a boolean-like value.")

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def normalize_environment(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("ENVIRONMENT must be a string.")
        normalized = value.strip().lower()
        aliases = {
            "dev": "development",
            "development": "development",
            "local": "development",
            "stage": "staging",
            "staging": "staging",
            "prod": "production",
            "production": "production",
        }
        if normalized not in aliases:
            raise ValueError("ENVIRONMENT must be development, staging, or production.")
        return aliases[normalized]

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if not self.is_production:
            return self

        weak_values = {
            "",
            "change-me",
            "change-me-in-production",
            "dev-secret-key-change-me",
            "dev-secret-key-change-me-in-production-abc123xyz789",
            "dev-jwt-secret",
            "dev-jwt-secret-change-me-in-production",
        }

        if self.DEBUG:
            raise ValueError("DEBUG must be disabled in production.")

        if self.SECRET_KEY in weak_values or len(self.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY must be replaced with a strong production secret.")

        if self.JWT_SECRET_KEY in weak_values or len(self.JWT_SECRET_KEY) < 32:
            raise ValueError("JWT_SECRET_KEY must be replaced with a strong production secret.")

        frontend_host = urlparse(self.FRONTEND_URL).hostname or ""
        if frontend_host in {"", "localhost", "127.0.0.1"}:
            raise ValueError("FRONTEND_URL must point to the real production frontend host.")

        return self

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


settings = Settings()
