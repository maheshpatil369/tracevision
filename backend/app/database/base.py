"""SQLAlchemy declarative base and shared mixins used by every model."""
from __future__ import annotations

import datetime
import uuid

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def generate_uuid() -> str:
    return str(uuid.uuid4())


class TimestampMixin:
    """created_at/updated_at columns shared by nearly every table."""
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.utcnow(), nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.utcnow(),
        onupdate=lambda: datetime.datetime.utcnow(), nullable=False)


class UUIDPKMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
