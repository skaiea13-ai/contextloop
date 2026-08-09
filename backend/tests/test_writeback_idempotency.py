from __future__ import annotations

import asyncio
import threading

import pytest
from httpx import ASGITransport, AsyncClient

from backend.contextloop import main
from backend.contextloop.models import ImpactAction, ImpactAssessment, PendingWriteBack

LOCAL_SESSION_TOKEN = "test-contextloop-session-token-with-32-bytes"
LOCAL_SESSION_HEADER = {"X-ContextLoop-Token": LOCAL_SESSION_TOKEN}
RUN_ID = "CL-IDEM"
WRITE_BACK_TOKEN = "a" * 64
OTHER_WRITE_BACK_TOKEN = "e" * 64
DOCUMENT_URN = "urn:li:document:shared-contextloop-idempotency-test"


def _pending() -> PendingWriteBack:
    return PendingWriteBack(
        run_id=RUN_ID,
        document_urn=DOCUMENT_URN,
        source_asset_urn="urn:li:dataset:test-source",
        related_asset_urns=["urn:li:dataset:test-downstream"],
        related_document_urns=[],
        column="discount_amount",
        change_type="drop_column",
        impact=ImpactAssessment(
            severity="P1",
            headline="Grounded test impact",
            summary="A deterministic write-back fixture.",
            why_it_matters="A reporting dependency is affected.",
            affected_asset_count=1,
            owner_count=1,
            business_reporting_asset_count=1,
            evidence=["One dependency was returned.", "The field is verified."],
            actions=[
                ImpactAction(
                    id=index,
                    title=f"Validate dependency {index}.",
                    owner="Catalog owner 01",
                    priority="now",
                )
                for index in range(1, 4)
            ],
        ),
    )


def _reset_state() -> None:
    main.pending_write_backs.clear()
    if hasattr(main, "in_flight_write_backs"):
        main.in_flight_write_backs.clear()
    if hasattr(main, "completed_write_backs"):
        main.completed_write_backs.clear()


@pytest.mark.asyncio
async def test_concurrent_writebacks_use_one_idempotent_document(monkeypatch) -> None:
    monkeypatch.setenv("CONTEXTLOOP_LOCAL_TOKEN", LOCAL_SESSION_TOKEN)
    _reset_state()
    main.pending_write_backs[WRITE_BACK_TOKEN] = _pending()
    save_entered = threading.Event()
    release_save = threading.Event()
    calls: list[dict[str, object]] = []

    def fake_save_incident_memory(**kwargs):
        calls.append(kwargs)
        save_entered.set()
        assert release_save.wait(timeout=3)
        return DOCUMENT_URN, "ContextLoop CL-IDEM: Grounded test impact"

    monkeypatch.setattr(main.datahub, "save_incident_memory", fake_save_incident_memory)
    payload = {
        "run_id": RUN_ID,
        "write_back_token": WRITE_BACK_TOKEN,
        "approved": True,
    }

    async with AsyncClient(
        transport=ASGITransport(app=main.app), base_url="http://127.0.0.1"
    ) as client:
        first = asyncio.create_task(
            client.post("/api/write-back", headers=LOCAL_SESSION_HEADER, json=payload)
        )
        assert await asyncio.to_thread(save_entered.wait, 1)
        concurrent = await client.post(
            "/api/write-back", headers=LOCAL_SESSION_HEADER, json=payload
        )
        release_save.set()
        first_response = await first
        replay = await client.post(
            "/api/write-back", headers=LOCAL_SESSION_HEADER, json=payload
        )

    assert first_response.status_code == 200
    assert concurrent.status_code == 409
    assert replay.status_code == 200
    assert replay.json() == first_response.json()
    assert len(calls) == 1
    assert calls[0]["document_urn"] == DOCUMENT_URN


@pytest.mark.asyncio
async def test_failed_writeback_retry_reuses_the_same_document_target(monkeypatch) -> None:
    monkeypatch.setenv("CONTEXTLOOP_LOCAL_TOKEN", LOCAL_SESSION_TOKEN)
    _reset_state()
    main.pending_write_backs[WRITE_BACK_TOKEN] = _pending()
    calls: list[dict[str, object]] = []

    def fake_save_incident_memory(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise RuntimeError("the first verification failed")
        return DOCUMENT_URN, "ContextLoop CL-IDEM: Grounded test impact"

    monkeypatch.setattr(main.datahub, "save_incident_memory", fake_save_incident_memory)
    payload = {
        "run_id": RUN_ID,
        "write_back_token": WRITE_BACK_TOKEN,
        "approved": True,
    }

    async with AsyncClient(
        transport=ASGITransport(app=main.app), base_url="http://127.0.0.1"
    ) as client:
        failed = await client.post(
            "/api/write-back", headers=LOCAL_SESSION_HEADER, json=payload
        )
        retried = await client.post(
            "/api/write-back", headers=LOCAL_SESSION_HEADER, json=payload
        )

    assert failed.status_code == 502
    assert retried.status_code == 200
    assert len(calls) == 2
    assert calls[0]["document_urn"] == calls[1]["document_urn"] == DOCUMENT_URN
    assert calls[0]["reviewed_at"] == calls[1]["reviewed_at"]


@pytest.mark.asyncio
async def test_cancelled_client_does_not_strand_an_approved_writeback(monkeypatch) -> None:
    monkeypatch.setenv("CONTEXTLOOP_LOCAL_TOKEN", LOCAL_SESSION_TOKEN)
    _reset_state()
    main.pending_write_backs[WRITE_BACK_TOKEN] = _pending()
    save_entered = threading.Event()
    release_save = threading.Event()
    calls = 0

    def fake_save_incident_memory(**_kwargs):
        nonlocal calls
        calls += 1
        save_entered.set()
        assert release_save.wait(timeout=3)
        return DOCUMENT_URN, "ContextLoop CL-IDEM: Grounded test impact"

    monkeypatch.setattr(main.datahub, "save_incident_memory", fake_save_incident_memory)
    payload = {
        "run_id": RUN_ID,
        "write_back_token": WRITE_BACK_TOKEN,
        "approved": True,
    }

    async with AsyncClient(
        transport=ASGITransport(app=main.app), base_url="http://127.0.0.1"
    ) as client:
        abandoned = asyncio.create_task(
            client.post("/api/write-back", headers=LOCAL_SESSION_HEADER, json=payload)
        )
        assert await asyncio.to_thread(save_entered.wait, 1)
        abandoned.cancel()
        with pytest.raises(asyncio.CancelledError):
            await abandoned
        release_save.set()
        for _ in range(100):
            if WRITE_BACK_TOKEN in getattr(main, "completed_write_backs", {}):
                break
            await asyncio.sleep(0.01)
        replay = await client.post(
            "/api/write-back", headers=LOCAL_SESSION_HEADER, json=payload
        )

    assert replay.status_code == 200
    assert calls == 1


@pytest.mark.asyncio
async def test_different_writebacks_are_serialized_without_dropping_pending_work(
    monkeypatch,
) -> None:
    monkeypatch.setenv("CONTEXTLOOP_LOCAL_TOKEN", LOCAL_SESSION_TOKEN)
    _reset_state()
    first_pending = _pending()
    second_pending = _pending().model_copy(
        update={
            "run_id": "CL-NEXT",
            "document_urn": "urn:li:document:shared-contextloop-next-test",
        }
    )
    main.pending_write_backs[WRITE_BACK_TOKEN] = first_pending
    main.pending_write_backs[OTHER_WRITE_BACK_TOKEN] = second_pending
    first_entered = threading.Event()
    release_first = threading.Event()
    calls = 0

    def fake_save_incident_memory(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            first_entered.set()
            assert release_first.wait(timeout=3)
        return kwargs["document_urn"], f"ContextLoop {kwargs['run_id']}: test"

    monkeypatch.setattr(main.datahub, "save_incident_memory", fake_save_incident_memory)
    first_payload = {
        "run_id": RUN_ID,
        "write_back_token": WRITE_BACK_TOKEN,
        "approved": True,
    }
    second_payload = {
        "run_id": "CL-NEXT",
        "write_back_token": OTHER_WRITE_BACK_TOKEN,
        "approved": True,
    }

    async with AsyncClient(
        transport=ASGITransport(app=main.app), base_url="http://127.0.0.1"
    ) as client:
        first = asyncio.create_task(
            client.post("/api/write-back", headers=LOCAL_SESSION_HEADER, json=first_payload)
        )
        assert await asyncio.to_thread(first_entered.wait, 1)
        overlapping = await client.post(
            "/api/write-back", headers=LOCAL_SESSION_HEADER, json=second_payload
        )
        release_first.set()
        assert (await first).status_code == 200
        second = await client.post(
            "/api/write-back", headers=LOCAL_SESSION_HEADER, json=second_payload
        )

    assert overlapping.status_code == 429
    assert second.status_code == 200
    assert calls == 2
