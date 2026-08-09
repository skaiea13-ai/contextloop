from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.contextloop import main

LOCAL_SESSION_TOKEN = "test-contextloop-session-token-with-32-bytes"
LOCAL_SESSION_HEADER = {"X-ContextLoop-Token": LOCAL_SESSION_TOKEN}


@pytest.mark.asyncio
async def test_privileged_api_rejects_missing_local_session_token(monkeypatch) -> None:
    monkeypatch.setenv("CONTEXTLOOP_LOCAL_TOKEN", LOCAL_SESSION_TOKEN)

    async with AsyncClient(
        transport=ASGITransport(app=main.app), base_url="http://127.0.0.1"
    ) as client:
        response = await client.post(
            "/api/write-back",
            json={"run_id": "CL-MISSING", "approved": True},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "A valid local session token is required."}


@pytest.mark.asyncio
async def test_privileged_api_accepts_matching_local_session_token(monkeypatch) -> None:
    monkeypatch.setenv("CONTEXTLOOP_LOCAL_TOKEN", LOCAL_SESSION_TOKEN)

    async with AsyncClient(
        transport=ASGITransport(app=main.app), base_url="http://127.0.0.1"
    ) as client:
        response = await client.post(
            "/api/write-back",
            headers=LOCAL_SESSION_HEADER,
            json={"run_id": "CL-MISSING", "approved": True},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_api_rejects_unexpected_host_before_route_execution(monkeypatch) -> None:
    monkeypatch.setenv("CONTEXTLOOP_LOCAL_TOKEN", LOCAL_SESSION_TOKEN)

    async with AsyncClient(
        transport=ASGITransport(app=main.app), base_url="http://attacker.example"
    ) as client:
        response = await client.post(
            "/api/write-back",
            headers=LOCAL_SESSION_HEADER,
            json={"run_id": "CL-MISSING", "approved": True},
        )

    assert response.status_code == 400
    assert response.text == "Invalid host header"


@pytest.mark.asyncio
async def test_privileged_api_fails_closed_when_server_token_is_missing(monkeypatch) -> None:
    monkeypatch.delenv("CONTEXTLOOP_LOCAL_TOKEN", raising=False)

    async with AsyncClient(
        transport=ASGITransport(app=main.app), base_url="http://127.0.0.1"
    ) as client:
        response = await client.post(
            "/api/write-back",
            json={"run_id": "CL-MISSING", "approved": True},
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "The local session gate is not configured."}
