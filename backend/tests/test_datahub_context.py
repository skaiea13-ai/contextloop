import json

from backend.contextloop import datahub_service
from backend.contextloop.datahub_service import (
    DataHubService,
    _governance_context,
    _search_query,
)

ASSET_URN = (
    "urn:li:dataset:(urn:li:dataPlatform:dbt,"
    "b2fd91.ORDER_ENTRY_DB.analytics.order_details,PROD)"
)
DOWNSTREAM_URN = (
    "urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.order_rollup,PROD)"
)


class StubDataHubContext:
    def __init__(self, _client: object) -> None:
        pass

    def __enter__(self) -> "StubDataHubContext":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def test_search_query_normalizes_asset_names() -> None:
    assert _search_query("analytics.order_details") == "/q analytics+order+details"


def test_governance_context_projects_only_safe_signals() -> None:
    entity = {
        "editableProperties": {"description": "Critical orders table owned by person@example.com"},
        "properties": {
            "customProperties": [
                {"key": "business_critical", "value": "True"},
                {"key": "owner", "value": "person@example.com"},
            ]
        },
        "tags": {
            "tags": [{"tag": {"urn": "urn:li:tag:pii", "properties": {"name": "PII"}}}]
        },
        "glossaryTerms": {
            "terms": [
                {
                    "term": {
                        "urn": "urn:li:glossaryTerm:certified",
                        "properties": {"name": "Certified"},
                    }
                }
            ]
        },
        "domain": {"domain": {"properties": {"name": "Data Platform"}}},
        "structuredProperties": {
            "properties": [
                {
                    "structuredProperty": {"definition": {"displayName": "Data Quality Score"}},
                    "values": [{"numberValue": 91.5}],
                },
                {
                    "structuredProperty": {
                        "definition": {"displayName": "Data Owner Escalation Contact"}
                    },
                    "values": [{"stringValue": "person@example.com"}],
                },
            ]
        },
    }

    context = _governance_context(entity)

    assert context["tags"] == ["PII"]
    assert context["glossary_terms"] == ["Certified"]
    assert context["domain"] == "Data Platform"
    assert context["custom_properties"] == {"business_critical": "True"}
    assert context["structured_properties"] == {"Data Quality Score": 91.5}
    assert "[redacted-email]" in context["description"]
    assert "@" not in json.dumps(context)


def test_collect_context_uses_canonical_dataset_name_and_environment(monkeypatch) -> None:
    search_calls: list[str] = []

    def fake_search(*, query: str, **_kwargs: object) -> dict[str, object]:
        search_calls.append(query)
        return {"searchResults": [{"entity": {"urn": ASSET_URN}}]}

    monkeypatch.setattr(datahub_service, "DataHubContext", StubDataHubContext)
    monkeypatch.setattr(datahub_service, "search", fake_search)
    monkeypatch.setattr(
        datahub_service,
        "list_schema_fields",
        lambda **_kwargs: {"fields": [{"fieldPath": "discount_amount"}]},
    )
    monkeypatch.setattr(
        datahub_service,
        "get_lineage",
        lambda **_kwargs: {
            "downstreams": {
                "searchResults": [
                    {"entity": {"urn": ASSET_URN}},
                    {"entity": {"urn": DOWNSTREAM_URN}},
                    {"entity": {"urn": DOWNSTREAM_URN}},
                ],
                "total": 3,
            }
        },
    )
    monkeypatch.setattr(
        datahub_service,
        "get_entities",
        lambda _urns: [
            {
                "urn": ASSET_URN,
                "properties": {"name": "unqualified_request_alias"},
                "platform": {"name": "dbt"},
            }
        ],
    )
    monkeypatch.setattr(datahub_service, "_prior_incident_memories", lambda *_args: [])
    service = DataHubService()
    monkeypatch.setattr(service, "_client", lambda: object())

    context, source, nodes, edges, _timings = service.collect_context(
        asset_urn=ASSET_URN,
        asset_name="friendly request alias",
        column="discount_amount",
        change_type="drop_column",
        environment="DEV",
    )

    canonical_name = "b2fd91.ORDER_ENTRY_DB.analytics.order_details"
    assert search_calls == ["/q friendly+request+alias"]
    assert context["change"]["asset_name"] == canonical_name
    assert context["change"]["environment"] == "PROD"
    assert source.name == canonical_name
    assert [node.urn for node in nodes] == [ASSET_URN, DOWNSTREAM_URN]
    assert [asset["urn"] for asset in context["downstream_assets"]] == [DOWNSTREAM_URN]
    assert len(edges) == 1
