from __future__ import annotations

from typing import List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPKMixin


class User(Base, UUIDPKMixin, TimestampMixin):
    """An analyst/investigator account (spec section 25)."""
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), default="analyst", nullable=False)  # analyst | admin
    is_active: Mapped[bool] = mapped_column(default=True)

    cases: Mapped[List["Case"]] = relationship(back_populates="analyst")

    def to_dict(self) -> dict:
        return {
            "id": self.id, "username": self.username, "full_name": self.full_name,
            "email": self.email, "role": self.role, "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }
