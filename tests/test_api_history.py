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

    def test_delete_task_returns_deleted_and_removes_history(self, client, test_task_id):
        from app.task_manager import task_manager
        task_manager.mark_failed(test_task_id, "test cleanup")
        resp = client.delete(f"/api/tasks/{test_task_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"
        data = client.get("/api/history").json()
        assert all(item["task_id"] != test_task_id for item in data)

    def test_delete_task_cannot_delete_running_task(self, client, test_task_id):
        resp = client.delete(f"/api/tasks/{test_task_id}")
        assert resp.status_code == 409

    def test_delete_missing_task_returns_404(self, client):
        resp = client.delete("/api/tasks/missing-task")
        assert resp.status_code == 404