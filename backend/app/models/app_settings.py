"""ORM-Modell `app_settings` — Singleton mit verschlüsselten CalDAV-Credentials und Feature-Flags.

`caldav_password_enc` ist ein Fernet-Ciphertext (base64); Klartext-Passwörter
werden niemals persistiert. `last_reminder_at` wird vom Scheduler gesetzt und
vom Dashboard-Banner gelesen.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    caldav_username: Mapped[str | None] = mapped_column(String(200), nullable=True)
    caldav_password_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    caldav_calendar_name: Mapped[str] = mapped_column(
        String(100), nullable=False, default="Meal Plan"
    )
    caldav_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    last_reminder_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
