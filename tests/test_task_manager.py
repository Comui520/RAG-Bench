"""Unit tests for task manager."""

import pytest
from app.task_manager import (
    TaskManager,
    TaskPhase,
    task_manager,
)


@pytest.fixture(autouse=True)
def reset_task_manager():
    """Reset the global task manager between tests."""
    task_manager._tasks.clear()
    task_manager._events.clear()
    yield


class TestTaskManager:
    def test_start_task_returns_task_id(self):
        task_id = task_manager.start_task("http://rag.com", "sk-key")
        assert task_id
        assert isinstance(task_id, str)
        assert len(task_id) == 32

    def test_get_state_after_start(self):
        task_id = task_manager.start_task("http://rag.com", "sk-key")
        state = task_manager.get_state(task_id)
        assert state is not None
        assert state["status"] == "UPLOADING"

    def test_get_state_nonexistent_returns_none(self):
        assert task_manager.get_state("nonexistent") is None

    def test_update_phase(self):
        task_id = task_manager.start_task("http://rag.com", "sk-key")
        task_manager.update_phase(task_id, TaskPhase.GENERATING_GOLDENS, progress=0.3)
        state = task_manager.get_state(task_id)
        assert state["phase"] == "GENERATING_GOLDENS"
        assert state["status"] == "GENERATING_GOLDENS"
        assert state["progress"] == 0.3

    def test_set_awaiting_confirmation(self):
        task_id = task_manager.start_task("http://rag.com", "sk-key")
        task_manager.update_phase(task_id, TaskPhase.AWAITING_CONFIRM, progress=1.0)
        state = task_manager.get_state(task_id)
        assert state["status"] == "AWAITING_CONFIRM"

    def test_mark_completed(self):
        task_id = task_manager.start_task("http://rag.com", "sk-key")
        task_manager.mark_completed(task_id)
        state = task_manager.get_state(task_id)
        assert state["status"] == "COMPLETED"
        assert state["progress"] == 1.0

    def test_mark_failed(self):
        task_id = task_manager.start_task("http://rag.com", "sk-key")
        task_manager.mark_failed(task_id, "Something went wrong")
        state = task_manager.get_state(task_id)
        assert state["status"] == "FAILED"
        assert state["error_message"] == "Something went wrong"

    def test_set_confirmation_event(self):
        task_id = task_manager.start_task("http://rag.com", "sk-key")
        task_manager.set_confirmation_event(task_id)
        task_manager.signal_confirmation(task_id)
        state = task_manager.get_state(task_id)
        assert state.get("confirmed") is True
