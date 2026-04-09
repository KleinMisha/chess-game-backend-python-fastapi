"""
Pytest will auto-discover / import this file called 'conftest.py'. ]
This file defines fixtures/variables required for testing multiple layers.
"""

import os
import tempfile
from typing import Generator

import pytest
from pytest import Session as PyTestSession
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.db.schema import Base

# Setup an in-memory SQLite database for testing
IN_MEMORY_URL = "sqlite:///:memory:"

# Setup temporary database file for testing.
temp_db_file = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)


def pytest_sessionfinish(session: PyTestSession, exitstatus: int) -> None:
    """Cleanup after final test: Delete the temporary SQLite file after pytest finishes"""
    try:
        os.unlink(temp_db_file.name)
    except FileNotFoundError:
        pass


TEMP_DB_FILE_URL = f"sqlite:///{temp_db_file.name}"
engine = create_engine(
    TEMP_DB_FILE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autoflush=False, bind=engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
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
        db.close()
