"""Generate database session"""

from typing import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import config


def get_engine() -> Engine:
    return create_engine(config.db_url, echo=config.is_debug)


def get_db() -> Generator[Session]:
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
