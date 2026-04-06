"""Database tables / schema"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.core.shared_types import Status


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class DBGame(Base):
    __tablename__ = "games"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(unique=True, nullable=True)
    current_fen: Mapped[str]
    history_fen: Mapped[list[str]] = mapped_column(JSON, default=[])
    moves_uci: Mapped[list[str]] = mapped_column(JSON, default=[])
    registered_players: Mapped[dict[str, str]] = mapped_column(JSON)
    status: Mapped[Status]
    created_at: Mapped[datetime] = mapped_column(default=utc_now())
    updated_at: Mapped[datetime] = mapped_column(default=utc_now(), onupdate=utc_now())
