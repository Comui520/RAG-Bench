"""API tests for evaluate endpoint v2."""

import pytest


class TestEvaluateV2:
    def test_evaluate_with_model_configs(self, client, test_task_id):
        """POST /api/evaluate with full ModelConfig should start evaluation."""
        resp = client.post(
            "/api/evaluate",
            json={
                "rag_base_url": "https://rag.example.com/v1",
                "rag_api_key": "sk-test-key",
                "rag_model": "deepseek-chat",
                "eval_model": {
                    "provider": "deepseek", "model_name": "deepseek-chat",
                    "api_key": "sk-eval", "base_url": "https://api.deepseek.com",
                },
                "embed_model": {
                    "provider": "siliconflow", "model_name": "BAAI/bge-m3",
                    "api_key": "sk-embed", "base_url": "https://api.siliconflow.cn/v1",
                },
                "task_id": test_task_id,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == test_task_id

    def test_evaluate_duplicate_returns_409(self, client, test_task_id):
        """Starting evaluation on an already-running task should return 409."""
        # First start evaluation
        client.post(
            "/api/evaluate",
            json={
                "rag_base_url": "https://rag.example.com/v1",
                "rag_api_key": "sk-test-key",
                "rag_model": "deepseek-chat",
                "eval_model": {
                    "provider": "deepseek", "model_name": "deepseek-chat",
                    "api_key": "sk-eval", "base_url": "https://api.deepseek.com",
                },
                "embed_model": {
                    "provider": "siliconflow", "model_name": "BAAI/bge-m3",
                    "api_key": "sk-embed", "base_url": "https://api.siliconflow.cn/v1",
                },
                "task_id": test_task_id,
            },
        )
        # Manually set task to RUNNING_EVAL
        from app.task_manager import task_manager, TaskPhase
        task_manager.update_phase(test_task_id, TaskPhase.RUNNING_EVAL, progress=0.5)

        # Second request should be rejected
        resp = client.post(
            "/api/evaluate",
            json={
                "rag_base_url": "https://rag.example.com/v1",
                "rag_api_key": "sk-test-key",
                "rag_model": "deepseek-chat",
                "eval_model": {
                    "provider": "deepseek", "model_name": "deepseek-chat",
                    "api_key": "sk-eval", "base_url": "https://api.deepseek.com",
                },
                "embed_model": {
                    "provider": "siliconflow", "model_name": "BAAI/bge-m3",
                    "api_key": "sk-embed", "base_url": "https://api.siliconflow.cn/v1",
                },
                "task_id": test_task_id,
            },
        )
        assert resp.status_code == 409

    def test_evaluate_missing_model_config_returns_422(self, client, test_task_id):
        """eval_model should be validatable."""
        resp = client.post(
            "/api/evaluate",
            json={
                "rag_base_url": "https://rag.example.com/v1",
                "rag_api_key": "sk-test-key",
                "task_id": test_task_id,
            },
        )
        assert resp.status_code == 422
