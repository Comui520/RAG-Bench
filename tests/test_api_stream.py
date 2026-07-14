"""API tests for SSE stream endpoint."""

import json
import pytest


class TestStreamEndpoint:
    @pytest.mark.asyncio
    async def test_stream_returns_events(self, client, test_task_id):
        """SSE endpoint should stream progress events."""
        from app.task_manager import task_manager

        import httpx
        from httpx import ASGITransport

        await task_manager.push_event(
            test_task_id, "progress",
            {"phase": "TEST", "progress": 0.5, "message": "testing"},
        )
        await task_manager.push_event(
            test_task_id, "complete",
            {"phase": "COMPLETED", "progress": 1.0},
        )

        async with httpx.AsyncClient(transport=ASGITransport(app=client.app), base_url="http://test") as ac:
            async with ac.stream("GET", f"/api/task/{test_task_id}/stream") as response:
                assert response.status_code == 200
                lines = []
                async for line in response.aiter_lines():
                    lines.append(line)
                event_text = "\n".join(lines)
                assert "event: progress" in event_text
                assert "event: complete" in event_text
                assert "phase" in event_text

    def test_stream_nonexistent_task_returns_404(self, client):
        resp = client.get("/api/task/nonexistent/stream")
        assert resp.status_code == 404
