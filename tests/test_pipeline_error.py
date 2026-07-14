"""Integration tests for error handling in the pipeline."""

import pytest
from app.pipeline import run_evaluation_pipeline
from app.models import ModelConfig


class TestPipelineErrors:
    def test_empty_docs_raises(self, temp_data_dir):
        """Pipeline should fail gracefully with empty documents."""
        from app.task_manager import task_manager
        from app.db import init_db, create_task
        init_db(":memory:")
        task_id = task_manager.start_task("http://test.com", "sk")
        create_task("http://test.com", "sk", task_id=task_id)

        eval_config = ModelConfig(
            provider="deepseek", model_name="deepseek-chat",
            api_key="sk-test", base_url="https://api.deepseek.com",
        )
        embed_config = ModelConfig(
            provider="siliconflow", model_name="BAAI/bge-m3",
            api_key="sk-test", base_url="https://api.siliconflow.cn/v1",
        )

        import asyncio
        asyncio.run(run_evaluation_pipeline(task_id, eval_config, embed_config))

        state = task_manager.get_state(task_id)
        assert state["status"] == "FAILED"
        assert state["error_message"] is not None
