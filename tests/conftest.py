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


@pytest.fixture
def db_session_repo() -> Generator[Session]:
    """Connection to a test database. Tables are removed at teardown to make unit tests of repository independent of each other."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        Base.metadata.drop_all(bind=engine)
        db.close()


@pytest.fixture
def db_session_shared() -> Generator[Session]:
    """Connection to a test database. Mock real setup with multiple sessions connecting to the same engine / database tables."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
