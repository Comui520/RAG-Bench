"""API tests for file upload endpoint."""

class TestUploadEndpoint:
    def test_upload_single_file_returns_200(self, client):
        content = b"This is a test document content."
        resp = client.post(
            "/api/upload",
            files={"files": ("doc.txt", content, "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data
        assert len(data["files"]) == 1
        assert data["files"][0]["filename"] == "doc.txt"

    def test_upload_multiple_files(self, client):
        resp = client.post(
            "/api/upload",
            files=[
                ("files", ("a.txt", b"content a", "text/plain")),
                ("files", ("b.txt", b"content b", "text/plain")),
            ],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["files"]) == 2

    def test_upload_no_file_returns_422(self, client):
        resp = client.post("/api/upload")
        assert resp.status_code == 422

    def test_upload_unsupported_extension_returns_400(self, client):
        resp = client.post(
            "/api/upload",
            files={"files": ("image.png", b"fake png", "image/png")},
        )
        assert resp.status_code == 400
        assert "Unsupported" in resp.json()["detail"]
