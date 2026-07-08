"""Unit tests for database module."""

import json
import sqlite3
import pytest
from pathlib import Path
from app.db import (
    get_db,
    init_db,
    create_task,
    get_task,
    update_task_status,
    add_document,
    get_documents,
    add_golden,
    get_goldens,
    save_eval_result,
    get_eval_results,
    get_all_tasks,
    VALID_STATUSES,
    TERMINAL_STATUSES,
)


@pytest.fixture
def db_conn():
    """In-memory SQLite database for isolated testing."""
    import app.db as db_mod
    db_mod._db_path = ":memory:"
    conn = init_db()
    yield conn
    conn.close()
    db_mod._db = None


class TestTaskCRUD:
    def test_create_and_get_task(self, db_conn):
        task_id = create_task(
            rag_base_url="https://rag.example.com/v1",
            rag_api_key="sk-test-123",
        )
        task = get_task(task_id)
        assert task["id"] == task_id
        assert task["rag_base_url"] == "https://rag.example.com/v1"
        assert task["rag_api_key"] == "sk-test-123"
        assert task["status"] == "UPLOADING"
        assert task["error_message"] is None
        assert task["created_at"] is not None
        assert task["completed_at"] is None

    def test_get_nonexistent_task_returns_none(self, db_conn):
        assert get_task("nonexistent-id") is None

    def test_get_all_tasks(self, db_conn):
        create_task(rag_base_url="http://a.com", rag_api_key="k1")
        create_task(rag_base_url="http://b.com", rag_api_key="k2")
        tasks = get_all_tasks()
        assert len(tasks) == 2

    def test_get_all_tasks_returns_empty_list(self, db_conn):
        assert get_all_tasks() == []


class TestStatusTransitions:
    def test_valid_transition(self, db_conn):
        task_id = create_task(rag_base_url="http://x.com", rag_api_key="k")
        update_task_status(task_id, "GENERATING_GOLDENS")
        task = get_task(task_id)
        assert task["status"] == "GENERATING_GOLDENS"

    def test_transition_to_completed_sets_timestamp(self, db_conn):
        task_id = create_task(rag_base_url="http://x.com", rag_api_key="k")
        for status in ["GENERATING_GOLDENS", "AWAITING_CONFIRM", "RUNNING_EVAL", "COMPLETED"]:
            update_task_status(task_id, status)
        task = get_task(task_id)
        assert task["status"] == "COMPLETED"
        assert task["completed_at"] is not None

    def test_transition_from_completed_raises(self, db_conn):
        task_id = create_task(rag_base_url="http://x.com", rag_api_key="k")
        for s in ["GENERATING_GOLDENS", "AWAITING_CONFIRM", "RUNNING_EVAL", "COMPLETED"]:
            update_task_status(task_id, s)
        with pytest.raises(ValueError, match="Cannot transition from COMPLETED"):
            update_task_status(task_id, "RUNNING_EVAL")

    def test_set_failed_stores_error(self, db_conn):
        task_id = create_task(rag_base_url="http://x.com", rag_api_key="k")
        update_task_status(task_id, "FAILED", error_message="Synthesizer crashed")
        task = get_task(task_id)
        assert task["status"] == "FAILED"
        assert task["error_message"] == "Synthesizer crashed"
        assert task["completed_at"] is not None


class TestDocuments:
    def test_add_and_get_documents(self, db_conn):
        task_id = create_task(rag_base_url="http://x.com", rag_api_key="k")
        add_document(task_id, "doc1.txt", "./data/abc/docs/doc1.txt", 1024)
        add_document(task_id, "doc2.md", "./data/abc/docs/doc2.md", 2048)
        docs = get_documents(task_id)
        assert len(docs) == 2
        assert docs[0]["filename"] == "doc1.txt"
        assert docs[1]["file_size"] == 2048

    def test_get_documents_empty_task(self, db_conn):
        task_id = create_task(rag_base_url="http://x.com", rag_api_key="k")
        assert get_documents(task_id) == []


class TestGoldens:
    def test_add_and_get_goldens(self, db_conn):
        task_id = create_task(rag_base_url="http://x.com", rag_api_key="k")
        add_golden(task_id, "What is X?", "X is a thing.", '["chunk1"]')
        add_golden(task_id, "What is Y?", "Y is another.", '["chunk2"]')
        goldens = get_goldens(task_id)
        assert len(goldens) == 2
        assert goldens[0]["input"] == "What is X?"
        assert goldens[0]["expected_output"] == "X is a thing."
        assert isinstance(goldens[0]["context"], str)

    def test_get_goldens_empty_task(self, db_conn):
        task_id = create_task(rag_base_url="http://x.com", rag_api_key="k")
        assert get_goldens(task_id) == []


class TestEvalResults:
    def test_save_and_get_results(self, db_conn):
        task_id = create_task(rag_base_url="http://x.com", rag_api_key="k")
        gid = add_golden(task_id, "Q?", "A.", '["c"]')
        metrics = {"FaithfulnessMetric": 0.92, "AnswerRelevancyMetric": 0.85}
        save_eval_result(task_id, gid, "The answer.", '["ctx"]', metrics, True)
        results = get_eval_results(task_id)
        assert len(results) == 1
        parsed = json.loads(results[0]["metrics_json"])
        assert parsed["FaithfulnessMetric"] == 0.92

    def test_get_results_empty_task(self, db_conn):
        task_id = create_task(rag_base_url="http://x.com", rag_api_key="k")
        assert get_eval_results(task_id) == []
