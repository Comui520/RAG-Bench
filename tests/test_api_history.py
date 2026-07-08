"""API tests for history endpoint."""

class TestHistoryEndpoint:
    def test_history_returns_list(self, client):
        resp = client.get("/api/history")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_history_includes_created_tasks(self, client, test_task_id):
        resp = client.get("/api/history")
        data = resp.json()
        assert any(item["task_id"] == test_task_id for item in data)
