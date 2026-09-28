from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

class EnvSettings(BaseSettings):
    BACKEND_ENV: Optional[str] = None
    EMAIL_SERVICE_KEY: Optional[str] = None
    PASSPORT_BROKER_SERVICE_URL: Optional[str] = None
    COUCHBASE_HOST: Optional[str] = None
    COUCHBASE_BUCKET: Optional[str] = None
    COUCHBASE_USER: Optional[str] = None
    COUCHBASE_PASSWORD: Optional[str] = None
    COUCHBASE_TOTAL_MEMORY_QUOTA: Optional[int] = None
    MINIO_DOMAIN: Optional[str] = None
    MINIO_REGION: Optional[str] = None
    MINIO_USER: Optional[str] = None
    MINIO_PASSWORD: Optional[str] = None
    ENCRYPTION_SECRET_KET: Optional[str] = None
    AUTH_SECRET_KEY: Optional[str] = None
    REFRESH_TOKEN_KEY: Optional[str] = None
    AUTH_ALGORITHM: Optional[str] = None
    EXPIRATION_TIME_MINUTES: Optional[int] = None
    FRONTEND_URL: Optional[str] = None
    DOCUMENTATION_URL: Optional[str] = None
    CA_CERT_PATH: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",  # Missing .env is fine; process environment values take precedence.
        env_file_encoding="utf-8",
        extra="allow",
    )
