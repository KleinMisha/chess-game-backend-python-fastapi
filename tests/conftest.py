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
