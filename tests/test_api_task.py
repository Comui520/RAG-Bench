"""API tests for task status endpoint."""

class TestTaskStatusEndpoint:
    def test_get_task_status(self, client, test_task_id):
        resp = client.get(f"/api/task/{test_task_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == test_task_id
        assert "status" in data

    def test_nonexistent_task_returns_404(self, client):
        resp = client.get("/api/task/nonexistent")
        assert resp.status_code == 404
