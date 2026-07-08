"""Shared pytest fixtures for API and integration tests."""

import os
import tempfile
import pytest
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.fixture
def temp_data_dir():
    """Temporary data directory for test isolation."""
    with tempfile.TemporaryDirectory() as tmp:
        import app.config
        original_data = app.config.DATA_DIR
        original_db = app.config.DATABASE_URL
        app.config.DATA_DIR = tmp
        app.config.DATABASE_URL = ":memory:"
        import app.db as db_mod
        db_mod._db = None
        db_mod._db_path = None
        yield Path(tmp)
        app.config.DATA_DIR = original_data
        app.config.DATABASE_URL = original_db
        db_mod._db = None
        db_mod._db_path = None


@pytest.fixture
def client(temp_data_dir):
    """FastAPI TestClient with isolated temp dir and in-memory DB."""
    from app.main import create_app
    app = create_app()
    import app.task_manager as tm
    tm.task_manager._tasks.clear()
    tm.task_manager._events.clear()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def test_task_id(client):
    """Create a task and upload a test file, return task_id."""
    content = b"This is a test document about a fictional product called WidgetX. WidgetX is a revolutionary tool for managing tasks."
    resp = client.post(
        "/api/upload",
        files={"files": ("test_doc.txt", content, "text/plain")},
    )
    assert resp.status_code == 200
    return resp.json()["task_id"]
