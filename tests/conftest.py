"""
Pytest will auto-discover / import this file called 'conftest.py'. ]
This file defines fixtures/variables required for testing multiple layers.
"""

from typing import Generator

import pytest
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.db.schema import Base

# Setup an in-memory SQLite database for testing
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autoflush=False, bind=engine)


def db_session(clear_db: bool) -> Generator[Session]:
    """
    Connect to a test database.
    -----
    Test database is in-memory SQLite database.
    parameters::
        clear_db [bool] : Remove tables at teardown (when True) or persist tables between calls (when False)
    """
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        if clear_db:
            Base.metadata.drop_all(bind=engine)
        db.close()


@pytest.fixture
def db_session_repo() -> Generator[Session]:
    """Connection to a test database. Tables are removed at teardown to make unit tests of repository independent of each other."""
    yield from db_session(clear_db=True)


@pytest.fixture
def db_session_shared() -> Generator[Session]:
    """Connection to a test database. Mock real setup with multiple sessions connecting to the same engine / database tables."""
    yield from db_session(clear_db=False)
