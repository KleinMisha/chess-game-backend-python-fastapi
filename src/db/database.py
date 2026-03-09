"""Generate database session"""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import config
from src.db.schema import Base

engine = create_engine(config.db_url, echo=config.is_debug)
SessionLocal = sessionmaker(bind=engine)

# Ensure all tables are created
Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
