"""Run backend tests against an Alembic-managed temporary SQLite database."""

import asyncio
import os
from pathlib import Path
import tempfile

from alembic import command
from alembic.config import Config
import pytest


_fd, _database_path = tempfile.mkstemp(prefix="baby_english_test_", suffix=".sqlite3")
os.close(_fd)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_database_path}"


@pytest.fixture(scope="session", autouse=True)
def migrated_test_database():
    command.upgrade(Config("alembic.ini"), "head")
    try:
        yield
    finally:
        from server.app.persistence.database import engine

        asyncio.run(engine.dispose())
        Path(_database_path).unlink(missing_ok=True)
