"""API tests for goldens endpoints."""

class TestGoldensEndpoint:
    def test_get_goldens_empty_returns_list(self, client, test_task_id):
        resp = client.get(f"/api/goldens/{test_task_id}")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_goldens_nonexistent_task_returns_empty(self, client):
        resp = client.get("/api/goldens/nonexistent")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_confirm_without_goldens_returns_409(self, client, test_task_id):
        resp = client.post(f"/api/goldens/{test_task_id}/confirm")
        assert resp.status_code in [400, 409]
