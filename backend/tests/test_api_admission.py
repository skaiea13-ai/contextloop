from __future__ import annotations

import asyncio
import threading
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from backend.contextloop import main
from backend.contextloop.models import GraphNode, ImpactAction, ImpactAssessment

LOCAL_SESSION_TOKEN = "test-contextloop-session-token-with-32-bytes"
LOCAL_SESSION_HEADER = {"X-ContextLoop-Token": LOCAL_SESSION_TOKEN}


def _analysis_fixture():
    source = GraphNode(
        id="source",
        urn="urn:li:dataset:(urn:li:dataPlatform:dbt,db.source,PROD)",
        name="db.source",
        platform="dbt",
        column="discount_amount",
        selected=True,
    )
    context = {
        "change": {
            "asset_urn": source.urn,
            "asset_name": source.name,
            "column": source.column,
            "change_type": "drop_column",
            "environment": "PROD",
        },
        "schema_match": [source.column],
        "source": source.model_dump(),
        "downstream_assets": [],
        "owner_names": [],
        "governance": {"signal_labels": []},
        "governance_signal_count": 0,
        "prior_incident_memories": [],
    }
    impact = ImpactAssessment(
        severity="P2",
        headline="No verified downstream assets at risk",
        summary="A deterministic admission-control fixture.",
        why_it_matters="The source schema still requires validation.",
        affected_asset_count=0,
        owner_count=0,
        business_reporting_asset_count=0,
        evidence=["The schema field is verified.", "No downstream assets were returned."],
        actions=[
            ImpactAction(
                id=index,
                title=f"Validate schema condition {index}.",
                owner="Unassigned",
                priority="now",
            )
            for index in range(1, 4)
        ],
    )
    return context, source, [source], [], [1, 1], impact


@pytest.mark.asyncio
async def test_analyze_rejects_a_second_concurrent_model_job(monkeypatch) -> None:
    monkeypatch.setenv("CONTEXTLOOP_LOCAL_TOKEN", LOCAL_SESSION_TOKEN)
    first_entered = threading.Event()
    release_first = threading.Event()
    calls = 0
    calls_lock = threading.Lock()
    context, source, nodes, edges, timings, impact = _analysis_fixture()

    def fake_collect_context(**_kwargs):
        nonlocal calls
        with calls_lock:
            calls += 1
            ordinal = calls
        if ordinal == 1:
            first_entered.set()
            assert release_first.wait(timeout=3)
        return context, source, nodes, edges, timings

    monkeypatch.setattr(main.datahub, "collect_context", fake_collect_context)
    monkeypatch.setattr(main.codex, "analyze", lambda _context: (impact, "fixture"))
    request = {
        "asset_urn": source.urn,
        "asset_name": source.name,
        "column": source.column,
        "change_type": "drop_column",
        "environment": "PROD",
    }

    async with AsyncClient(
        transport=ASGITransport(app=main.app), base_url="http://127.0.0.1"
    ) as client:
        first = asyncio.create_task(
            client.post("/api/analyze", headers=LOCAL_SESSION_HEADER, json=request)
        )
        assert await asyncio.to_thread(first_entered.wait, 1)
        second = await client.post(
            "/api/analyze", headers=LOCAL_SESSION_HEADER, json=request
        )
        release_first.set()
        first_response = await first

    assert first_response.status_code == 200
    assert second.status_code == 429
    assert second.json() == {
        "detail": "Another impact analysis is already running for this local session."
    }
    assert calls == 1


@pytest.mark.asyncio
async def test_short_display_id_collision_cannot_overwrite_writeback_capabilities(
    monkeypatch,
) -> None:
    monkeypatch.setenv("CONTEXTLOOP_LOCAL_TOKEN", LOCAL_SESSION_TOKEN)
    main.pending_write_backs.clear()
    main.in_flight_write_backs.clear()
    main.completed_write_backs.clear()
    context, source, nodes, edges, timings, impact = _analysis_fixture()
    identifiers = iter(
        [
            SimpleNamespace(hex="abcd" + "1" * 28),
            SimpleNamespace(hex="abcd" + "2" * 28),
        ]
    )
    capabilities = iter(["1" * 64, "2" * 64])
    monkeypatch.setattr(main, "uuid4", lambda: next(identifiers))
    monkeypatch.setattr(main, "token_hex", lambda _size: next(capabilities))
    monkeypatch.setattr(
        main.datahub,
        "collect_context",
        lambda **_kwargs: (context, source, nodes, edges, timings),
    )
    monkeypatch.setattr(main.codex, "analyze", lambda _context: (impact, "fixture"))
    request = {
        "asset_urn": source.urn,
        "asset_name": source.name,
        "column": source.column,
        "change_type": "drop_column",
        "environment": "PROD",
    }

    async with AsyncClient(
        transport=ASGITransport(app=main.app), base_url="http://127.0.0.1"
    ) as client:
        first = await client.post(
            "/api/analyze", headers=LOCAL_SESSION_HEADER, json=request
        )
        second = await client.post(
            "/api/analyze", headers=LOCAL_SESSION_HEADER, json=request
        )

    first_payload = first.json()
    second_payload = second.json()
    assert first.status_code == second.status_code == 200
    assert first_payload["run_id"] == second_payload["run_id"] == "CL-ABCD"
    assert first_payload["write_back_token"] != second_payload["write_back_token"]
    assert set(main.pending_write_backs) == {"1" * 64, "2" * 64}
    assert {
        pending.document_urn for pending in main.pending_write_backs.values()
    } == {
        f"urn:li:document:shared-contextloop-{'abcd' + '1' * 28}",
        f"urn:li:document:shared-contextloop-{'abcd' + '2' * 28}",
    }
