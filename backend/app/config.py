"""Application configuration loaded from environment."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://lcms:changeme@localhost:5432/lcms"
    jwt_secret: str = "change-this-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 30
    refresh_token_ttl_days: int = 7
    cors_origins: str = "http://localhost:18780,http://localhost:18717"
    model_storage_path: str = "./models"
    pubchem_base_url: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

    # Default admin user (seeded on first startup)
    admin_email: str = "admin@example.com"
    admin_password: str = "changeme-admin-2024!"

    # SMTP settings for password reset emails
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@isotopiq.app"
    smtp_from_name: str = "IsotopiQ"
    smtp_use_tls: bool = True
    # Frontend URL for building reset links
    frontend_url: str = "http://localhost:18780"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
