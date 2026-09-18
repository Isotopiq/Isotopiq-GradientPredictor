"""Application configuration loaded from environment."""
from __future__ import annotations

import logging

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_DEFAULT_JWT_SECRET = "change-this-to-a-long-random-string"
_DEFAULT_ADMIN_PASSWORD = "changeme-admin-2024!"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # "production" enforces that secrets are explicitly configured
    app_env: str = "development"

    database_url: str = "postgresql+asyncpg://lcms:changeme@localhost:5432/lcms"
    jwt_secret: str = _DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 30
    refresh_token_ttl_days: int = 7
    cors_origins: str = "http://localhost:18780,http://localhost:18717"
    model_storage_path: str = "./models"
    pubchem_base_url: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

    # Default admin user (seeded on first startup)
    admin_email: str = "admin@example.com"
    admin_password: str = _DEFAULT_ADMIN_PASSWORD

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

    @model_validator(mode="after")
    def _check_production_secrets(self) -> "Settings":
        """Replace publicly known default secrets with ephemeral random ones.

        In production we never boot with repo-known secrets — that would let
        anyone forge admin JWTs or log in with the documented default admin
        password. Instead of refusing to start (which silently bricks a
        compose deploy where the env vars were never set), we generate strong
        ephemeral values and warn loudly:

        - JWT_SECRET: random per boot. Tokens issued before a restart are
          invalidated — set JWT_SECRET for stable sessions.
        - ADMIN_PASSWORD: random per boot and printed to the container log at
          seed time — set ADMIN_PASSWORD for a persistent admin password.
        """
        if self.app_env.lower() not in ("production", "prod"):
            return self
        import secrets as _secrets

        if self.jwt_secret == _DEFAULT_JWT_SECRET:
            self.jwt_secret = _secrets.token_urlsafe(48)
            logger.warning(
                "PRODUCTION MODE: JWT_SECRET was unset/default — generated an "
                "ephemeral secret. All sessions are invalidated on every "
                "restart. Set JWT_SECRET in the environment for stable logins."
            )
        if self.admin_password == _DEFAULT_ADMIN_PASSWORD:
            self.admin_password = _secrets.token_urlsafe(24)
            logger.warning(
                "PRODUCTION MODE: ADMIN_PASSWORD was unset/default — generated "
                "an ephemeral admin password (visible in the seed log line). "
                "It changes on every restart. Set ADMIN_PASSWORD in the "
                "environment for a persistent admin password."
            )
        return self


settings = Settings()
