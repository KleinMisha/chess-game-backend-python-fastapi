"""Database tables / schema"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class DBGame(Base):
    __tablename__ = "games"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    current_fen: Mapped[str]
    history_fen: Mapped[list[str]] = mapped_column(JSON, default=[])
    moves_uci: Mapped[list[str]] = mapped_column(JSON, default=[])
    registered_players: Mapped[dict[str, str]] = mapped_column(JSON)
    status: Mapped[str]
    winner: Mapped[
        Optional[str]
    ]  # TODO: check how to deal with this neatly. Game simply computes the winner. So would break GameModel as contract ?
    created_at: Mapped[datetime] = mapped_column(default=utc_now())
    updated_at: Mapped[datetime] = mapped_column(default=utc_now(), onupdate=utc_now())
