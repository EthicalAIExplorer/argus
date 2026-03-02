from __future__ import annotations

import json

from fastapi.testclient import TestClient

from argus.mcp_server import create_app


def _auth_header() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}


def test_mcp_tools_list_requires_auth(monkeypatch) -> None:
    monkeypatch.setenv("ARGUS_AUTH_TOKEN", "test-token")
    app = create_app()
    client = TestClient(app)

    unauth = client.post("/", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    assert unauth.status_code == 401

    auth = client.post(
        "/",
        headers=_auth_header(),
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
    )
    assert auth.status_code == 200
    body = auth.json()
    names = [tool["name"] for tool in body["result"]["tools"]]
    assert "argus_pipeline_status" in names


def test_mcp_get_digest_tool(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ARGUS_AUTH_TOKEN", "test-token")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "digests").mkdir()
    (tmp_path / "digests/2026-03-02.md").write_text("# Digest", encoding="utf-8")

    app = create_app()
    client = TestClient(app)

    resp = client.post(
        "/",
        headers=_auth_header(),
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "argus_get_digest", "arguments": {"date": "2026-03-02"}},
        },
    )
    assert resp.status_code == 200
    payload = json.loads(resp.json()["result"]["content"][0]["text"])
    assert payload["exists"] is True
    assert "# Digest" in payload["digest"]


def test_mcp_get_digest_rejects_non_date_input(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ARGUS_AUTH_TOKEN", "test-token")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "digests").mkdir()
    (tmp_path / "README.md").write_text("secret", encoding="utf-8")

    app = create_app()
    client = TestClient(app)

    resp = client.post(
        "/",
        headers=_auth_header(),
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "argus_get_digest", "arguments": {"date": "../README"}},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"]["code"] == -32602
    assert "YYYY-MM-DD" in body["error"]["message"]
