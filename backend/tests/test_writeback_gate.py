import pytest
from datahub.sdk import Document
from httpx import ASGITransport, AsyncClient

from backend.contextloop import datahub_service, main
from backend.contextloop.datahub_service import (
    DataHubService,
    DataHubWriteBackError,
    _document_urn_from_save_result,
    _verify_saved_document,
)
from backend.contextloop.models import ImpactAction, ImpactAssessment, PendingWriteBack

SOURCE_URN = "urn:li:dataset:(urn:li:dataPlatform:dbt,db.source,PROD)"
DOWNSTREAM_URN = "urn:li:dataset:(urn:li:dataPlatform:looker,report.orders,PROD)"
PRIOR_DOCUMENT_URN = "urn:li:document:prior"
SAVED_DOCUMENT_URN = "urn:li:document:verified"


class StubDataHubContext:
    def __init__(self, _client: object) -> None:
        pass

    def __enter__(self) -> "StubDataHubContext":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class FakeEntities:
    def __init__(self) -> None:
        self.document: Document | None = None
        self.get_calls: list[str] = []

    def get(self, urn: str) -> Document:
        self.get_calls.append(urn)
        assert self.document is not None
        return self.document


class FakeClient:
    def __init__(self) -> None:
        self.entities = FakeEntities()


def assessment() -> ImpactAssessment:
    return ImpactAssessment(
        severity="P1",
        headline="Grounded test impact",
        summary="A deterministic test assessment.",
        why_it_matters="A reporting dependency is affected.",
        affected_asset_count=1,
        owner_count=1,
        business_reporting_asset_count=1,
        evidence=["DataHub returned one downstream asset.", "The asset is a BI report."],
        actions=[
            ImpactAction(
                id=index,
                title=f"Validate downstream dependency {index}.",
                owner="Data Platform Team",
                priority="now",
            )
            for index in range(1, 4)
        ],
    )


@pytest.mark.asyncio
async def test_writeback_rejects_unknown_run() -> None:
    main.pending_write_backs.clear()
    async with AsyncClient(
        transport=ASGITransport(app=main.app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/write-back",
            json={"run_id": "CL-MISSING", "approved": True},
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_writeback_uses_server_side_grounded_payload(monkeypatch) -> None:
    run_id = "CL-TEST"
    main.pending_write_backs.clear()
    main.pending_write_backs[run_id] = PendingWriteBack(
        source_asset_urn="urn:li:dataset:test-source",
        related_asset_urns=["urn:li:dataset:test-downstream"],
        related_document_urns=["urn:li:document:prior"],
        column="discount_amount",
        change_type="drop_column",
        impact=assessment(),
    )
    captured: dict[str, object] = {}

    def fake_save_incident_memory(**kwargs):
        captured.update(kwargs)
        return "urn:li:document:test", "Grounded test impact"

    monkeypatch.setattr(main.datahub, "save_incident_memory", fake_save_incident_memory)
    async with AsyncClient(
        transport=ASGITransport(app=main.app), base_url="http://test"
    ) as client:
        tampered_response = await client.post(
            "/api/write-back",
            json={"run_id": run_id, "approved": True, "impact": {"headline": "tampered"}},
        )
        assert tampered_response.status_code == 422

        response = await client.post(
            "/api/write-back",
            json={"run_id": run_id, "approved": True},
        )

    assert response.status_code == 200
    assert captured["source_asset_urn"] == "urn:li:dataset:test-source"
    assert captured["related_asset_urns"] == ["urn:li:dataset:test-downstream"]
    assert captured["related_document_urns"] == ["urn:li:document:prior"]
    assert captured["impact"] == assessment()
    assert response.json()["datahub_url"] == (
        "http://localhost:9002/document/urn:li:document:test"
    )
    assert run_id not in main.pending_write_backs


@pytest.mark.asyncio
async def test_writeback_preserves_pending_analysis_when_verification_fails(monkeypatch) -> None:
    run_id = "CL-RETRY"
    pending = PendingWriteBack(
        source_asset_urn=SOURCE_URN,
        related_asset_urns=[DOWNSTREAM_URN],
        related_document_urns=[PRIOR_DOCUMENT_URN],
        column="discount_amount",
        change_type="drop_column",
        impact=assessment(),
    )
    main.pending_write_backs.clear()
    main.pending_write_backs[run_id] = pending

    def fake_save_incident_memory(**_kwargs):
        raise RuntimeError("credential-bearing internal integration detail")

    monkeypatch.setattr(main.datahub, "save_incident_memory", fake_save_incident_memory)
    async with AsyncClient(
        transport=ASGITransport(app=main.app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/write-back",
            json={"run_id": run_id, "approved": True},
        )

    assert response.status_code == 502
    assert response.json() == {
        "detail": (
            "DataHub write-back could not be verified. "
            "The pending analysis was preserved."
        )
    }
    assert "credential" not in response.text
    assert main.pending_write_backs[run_id] == pending


def test_save_incident_memory_requeries_and_verifies_persisted_document(monkeypatch) -> None:
    service = DataHubService()
    client = FakeClient()
    captured: dict[str, object] = {}

    def fake_save_document(**kwargs):
        captured.update(kwargs)
        client.entities.document = Document.create_document(
            id="verified",
            title=kwargs["title"],
            text=kwargs["content"],
            subtype=kwargs["document_type"],
            related_assets=kwargs["related_assets"],
            related_documents=kwargs["related_documents"],
        )
        return {"success": True, "urn": SAVED_DOCUMENT_URN}

    monkeypatch.setattr(datahub_service, "DataHubContext", StubDataHubContext)
    monkeypatch.setattr(datahub_service, "save_document", fake_save_document)
    monkeypatch.setattr(service, "_client", lambda: client)

    urn, title = service.save_incident_memory(
        run_id="CL-VERIFY",
        source_asset_urn=SOURCE_URN,
        related_asset_urns=[DOWNSTREAM_URN, DOWNSTREAM_URN],
        related_document_urns=[PRIOR_DOCUMENT_URN, PRIOR_DOCUMENT_URN],
        column="discount_amount",
        change_type="drop_column",
        impact=assessment(),
    )

    assert urn == SAVED_DOCUMENT_URN
    assert title == "ContextLoop CL-VERIFY: Grounded test impact"
    assert captured["document_type"] == "Analysis"
    assert captured["related_assets"] == [SOURCE_URN, DOWNSTREAM_URN]
    assert captured["related_documents"] == [PRIOR_DOCUMENT_URN]
    assert client.entities.get_calls == [SAVED_DOCUMENT_URN]


@pytest.mark.parametrize(
    "result",
    [
        {"success": False, "urn": SAVED_DOCUMENT_URN},
        {"success": True, "urn": "urn:li:dataset:not-a-document"},
        {"success": True, "urn": "not-a-urn"},
        {"success": True},
    ],
)
def test_save_result_requires_successful_valid_document_urn(result) -> None:
    with pytest.raises(DataHubWriteBackError):
        _document_urn_from_save_result(result)


@pytest.mark.parametrize(
    ("title", "text", "status", "subtype", "assets", "documents"),
    [
        (
            "ContextLoop CL-VERIFY: Grounded test impact",
            "# ContextLoop CL-VERIFY: Grounded test impact\n\n- Column: `discount_amount`",
            "PUBLISHED",
            "Note",
            [SOURCE_URN, DOWNSTREAM_URN],
            [PRIOR_DOCUMENT_URN],
        ),
        (
            "ContextLoop CL-VERIFY: Grounded test impact",
            "# ContextLoop CL-VERIFY: Grounded test impact\n\n- Column: `discount_amount`",
            "PUBLISHED",
            "Analysis",
            [SOURCE_URN],
            [PRIOR_DOCUMENT_URN],
        ),
        (
            "ContextLoop CL-VERIFY: Grounded test impact",
            "# ContextLoop CL-VERIFY: Grounded test impact\n\n- Column: `discount_amount`",
            "PUBLISHED",
            "Analysis",
            [SOURCE_URN, DOWNSTREAM_URN],
            [],
        ),
        (
            "Wrong title",
            "# ContextLoop CL-VERIFY: Grounded test impact\n\n- Column: `discount_amount`",
            "PUBLISHED",
            "Analysis",
            [SOURCE_URN, DOWNSTREAM_URN],
            [PRIOR_DOCUMENT_URN],
        ),
        (
            "ContextLoop CL-VERIFY: Grounded test impact",
            "# ContextLoop CL-VERIFY: Grounded test impact\n\nColumn omitted",
            "PUBLISHED",
            "Analysis",
            [SOURCE_URN, DOWNSTREAM_URN],
            [PRIOR_DOCUMENT_URN],
        ),
        (
            "ContextLoop CL-VERIFY: Grounded test impact",
            "# ContextLoop CL-VERIFY: Grounded test impact\n\n- Column: `discount_amount`",
            "UNPUBLISHED",
            "Analysis",
            [SOURCE_URN, DOWNSTREAM_URN],
            [PRIOR_DOCUMENT_URN],
        ),
    ],
)
def test_persisted_document_must_match_every_writeback_field(
    title: str,
    text: str,
    status: str,
    subtype: str,
    assets: list[str],
    documents: list[str],
) -> None:
    document = Document.create_document(
        id="verified",
        title=title,
        text=text,
        status=status,
        subtype=subtype,
        related_assets=assets,
        related_documents=documents,
    )

    with pytest.raises(DataHubWriteBackError):
        _verify_saved_document(
            document,
            document_urn=SAVED_DOCUMENT_URN,
            title="ContextLoop CL-VERIFY: Grounded test impact",
            content=(
                "# ContextLoop CL-VERIFY: Grounded test impact\n\n"
                "- Column: `discount_amount`"
            ),
            related_asset_urns=[SOURCE_URN, DOWNSTREAM_URN],
            related_document_urns=[PRIOR_DOCUMENT_URN],
        )
