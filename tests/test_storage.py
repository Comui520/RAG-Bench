"""Unit tests for file storage module."""

import os
import tempfile
import pytest
from pathlib import Path
from app.storage import (
    ensure_task_dir,
    save_uploaded_file,
    get_document_paths,
    delete_task_data,
    ALLOWED_EXTENSIONS,
)


@pytest.fixture
def data_dir():
    with tempfile.TemporaryDirectory() as tmp:
        import app.config
        original = app.config.DATA_DIR
        app.config.DATA_DIR = tmp
        yield Path(tmp)
        app.config.DATA_DIR = original


class TestEnsureTaskDir:
    def test_creates_task_directory(self, data_dir):
        task_id = "test-task-001"
        path = ensure_task_dir(task_id)
        assert path.exists()
        assert path.is_dir()
        assert path == data_dir / task_id

    def test_idempotent(self, data_dir):
        task_id = "test-task-001"
        ensure_task_dir(task_id)
        ensure_task_dir(task_id)


class TestSaveUploadedFile:
    def test_saves_file_to_task_dir(self, data_dir):
        task_id = "test-task-001"
        content = b"Hello, this is a test document."
        filepath = save_uploaded_file(task_id, "test.txt", content)
        assert os.path.exists(filepath)
        with open(filepath, "rb") as f:
            assert f.read() == content

    def test_rejects_unsupported_extension(self, data_dir):
        task_id = "test-task-001"
        with pytest.raises(ValueError, match="Unsupported file type"):
            save_uploaded_file(task_id, "image.png", b"fake png")


class TestGetDocumentPaths:
    def test_returns_all_files_in_docs_dir(self, data_dir):
        task_id = "test-task-001"
        save_uploaded_file(task_id, "a.txt", b"a")
        save_uploaded_file(task_id, "b.md", b"b")
        paths = get_document_paths(task_id)
        assert len(paths) == 2
        for p in paths:
            assert os.path.exists(p)

    def test_returns_empty_list_for_missing_dir(self, data_dir):
        assert get_document_paths("nonexistent-task") == []


class TestDeleteTaskData:
    def test_deletes_task_directory(self, data_dir):
        task_id = "test-task-001"
        save_uploaded_file(task_id, "doc.txt", b"content")
        assert ensure_task_dir(task_id).exists()
        delete_task_data(task_id)
        assert not (data_dir / task_id).exists()
