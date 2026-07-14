"""API tests for models proxy endpoint."""

import pytest
from unittest.mock import patch, MagicMock


class TestModelsEndpoint:
    def test_returns_model_list(self, client):
        """Mock a successful /models response from an external API."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"data": [{"id": "model-a"}, {"id": "model-b"}]}
            mock_get.return_value = mock_resp

            resp = client.get(
                "/api/models",
                params={"base_url": "https://api.example.com", "api_key": "sk-test"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["data"]) == 2
            assert data["data"][0]["id"] == "model-a"

    def test_returns_502_when_upstream_fails(self, client):
        """When the external API is unreachable, return 502."""
        from unittest.mock import AsyncMock
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")
            resp = client.get(
                "/api/models",
                params={"base_url": "https://bad.example.com", "api_key": "sk-test"},
            )
            assert resp.status_code == 502

    def test_missing_params_returns_422(self, client):
        """base_url and api_key are required."""
        resp = client.get("/api/models")
        assert resp.status_code == 422
