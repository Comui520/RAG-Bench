"""API tests for evaluate endpoint."""

class TestEvaluateEndpoint:
    def test_evaluate_returns_task_id(self, client, test_task_id):
        resp = client.post(
            "/api/evaluate",
            json={
                "rag_base_url": "https://rag.example.com/v1",
                "rag_api_key": "sk-test-key",
                "task_id": test_task_id,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == test_task_id

    def test_evaluate_missing_fields_returns_422(self, client):
        resp = client.post(
            "/api/evaluate",
            json={"rag_base_url": "http://x.com"},
        )
        assert resp.status_code == 422

    def test_evaluate_nonexistent_task_returns_404(self, client):
        resp = client.post(
            "/api/evaluate",
            json={
                "rag_base_url": "https://rag.example.com/v1",
                "rag_api_key": "sk-test",
                "task_id": "nonexistent",
            },
        )
        assert resp.status_code == 404
