"""Application settings ORM model (singleton key-value store for admin-configurable settings)."""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPK


class AppSettings(Base, UUIDPK, Timestamped):
    __tablename__ = "app_settings"

    # Branding
    lab_name: Mapped[str] = mapped_column(String(255), nullable=False, default="IsotopiQ")
    lab_subtitle: Mapped[str] = mapped_column(String(255), nullable=False, default="LC-MS Method Prediction Suite")
    lab_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    lab_website: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Logo (stored as PNG bytes)
    logo_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    logo_mime_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Report footer text
    report_footer: Mapped[str] = mapped_column(
        Text, nullable=False,
        default="Predictions are estimates derived from physicochemical heuristics and statistical models. "
                "They require experimental verification before use in regulated or production analytical work.",
    )

    # Allow admin to disable new user registration
    registration_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    @classmethod
    def default(cls) -> "AppSettings":
        return cls(
            lab_name="IsotopiQ",
            lab_subtitle="LC-MS Method Prediction Suite",
            report_footer="Predictions are estimates derived from physicochemical heuristics and statistical models. "
                          "They require experimental verification before use in regulated or production analytical work.",
            registration_enabled=True,
        )
