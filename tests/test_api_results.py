"""API tests for results endpoint."""

class TestResultsEndpoint:
    def test_results_incomplete_task_returns_404(self, client, test_task_id):
        resp = client.get(f"/api/results/{test_task_id}")
        assert resp.status_code == 404

    def test_results_nonexistent_task_returns_404(self, client):
        resp = client.get("/api/results/nonexistent")
        assert resp.status_code == 404
