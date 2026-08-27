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

    # ── 金标 CRUD ─────────────────────────────────────────
    def test_add_manual_golden(self, client, test_task_id):
        resp = client.post(
            f"/api/goldens/{test_task_id}",
            json={"input": "What is WidgetX?", "expected_output": "A task tool."},
        )
        assert resp.status_code == 200
        gid = resp.json()["id"]
        # 列表应包含新增内容
        gresp = client.get(f"/api/goldens/{test_task_id}")
        assert any(g["id"] == gid for g in gresp.json())

    def test_update_golden(self, client, test_task_id):
        gid = client.post(
            f"/api/goldens/{test_task_id}",
            json={"input": "q1", "expected_output": "a1"},
        ).json()["id"]
        resp = client.put(
            f"/api/goldens/{gid}",
            json={"input": "q1-edited", "expected_output": "a1-edited"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "updated"
        gresp = client.get(f"/api/goldens/{test_task_id}")
        updated = next(g for g in gresp.json() if g["id"] == gid)
        assert updated["input"] == "q1-edited"
        assert updated["expected_output"] == "a1-edited"

    def test_delete_golden(self, client, test_task_id):
        gid = client.post(
            f"/api/goldens/{test_task_id}",
            json={"input": "q", "expected_output": "a"},
        ).json()["id"]
        resp = client.delete(f"/api/goldens/{gid}")
        assert resp.status_code == 200
        gresp = client.get(f"/api/goldens/{test_task_id}")
        assert all(g["id"] != gid for g in gresp.json())

    def test_update_nonexistent_golden_returns_404(self, client):
        resp = client.put("/api/goldens/99999", json={"input": "x"})
        assert resp.status_code == 404

    def test_delete_nonexistent_golden_returns_404(self, client):
        resp = client.delete("/api/goldens/99999")
        assert resp.status_code == 404
