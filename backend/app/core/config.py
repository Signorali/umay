from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_ENV: str = "development"
    APP_DEBUG: bool = False
    APP_SECRET_KEY: str
    APP_NAME: str = "Umay"
    APP_VERSION: str = "0.1.0"

    # Database
    DATABASE_URL: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "umay"
    POSTGRES_USER: str = "umay"
    POSTGRES_PASSWORD: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    # Storage
    STORAGE_PATH: str = "/app/storage"
    MAX_UPLOAD_SIZE_MB: int = 10
    BACKUP_PATH: str = "/app/backups"
    BACKUP_ENCRYPTION_KEY: str = ""

    # First admin (installation wizard)
    FIRST_ADMIN_EMAIL: str = ""
    FIRST_ADMIN_PASSWORD: str = ""
    FIRST_TENANT_NAME: str = "Default"

    # License
    LICENSE_KEY: str = ""
    LICENSE_MODE: str = "trial"

    # Performance (Production Optimization)
    ENABLE_GZIP_COMPRESSION: bool = True
    ENABLE_RESPONSE_CACHING: bool = True
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_RECYCLE_SECONDS: int = 3600
    REDIS_CACHE_ENABLED: bool = True
    SLOW_QUERY_THRESHOLD_MS: int = 1000

    # Email / SMTP  (cloud.md §21 — notification foundation)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@umay.local"
    SMTP_FROM_NAME: str = "Umay"
    SMTP_TLS: bool = True
    SMTP_ENABLED: bool = False          # False = email silently skipped

    @property
    def smtp_configured(self) -> bool:
        return self.SMTP_ENABLED and bool(self.SMTP_HOST and self.SMTP_USERNAME)

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    # Google Calendar OAuth2
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:3000/api/v1/calendar/integrations/google/callback"

    # Microsoft / Outlook Calendar OAuth2
    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    MICROSOFT_TENANT_ID: str = "common"   # 'common' for personal+work accounts
    MICROSOFT_REDIRECT_URI: str = "http://localhost:3000/api/v1/calendar/integrations/microsoft/callback"

    @property
    def google_configured(self) -> bool:
        return bool(self.GOOGLE_CLIENT_ID and self.GOOGLE_CLIENT_SECRET)

    @property
    def microsoft_configured(self) -> bool:
        return bool(self.MICROSOFT_CLIENT_ID and self.MICROSOFT_CLIENT_SECRET)


settings = Settings()
