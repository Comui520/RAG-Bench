"""Integration tests for error handling in the pipeline."""

import pytest
from app.pipeline import run_evaluation_pipeline


class TestPipelineErrors:
    def test_empty_docs_raises(self, temp_data_dir):
        """Pipeline should fail gracefully with empty documents."""
        from app.task_manager import task_manager
        task_id = task_manager.start_task("http://test.com", "sk")

        import asyncio
        asyncio.run(run_evaluation_pipeline(task_id))

        state = task_manager.get_state(task_id)
        assert state["status"] == "FAILED"
        assert state["error_message"] is not None
