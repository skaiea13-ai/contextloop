from __future__ import annotations

import os
import re
import time
from datetime import datetime
from threading import Lock
from typing import Any

from datahub.metadata.urns import DatasetUrn, DocumentUrn
from datahub.sdk import DataHubClient, Document
from datahub_agent_context import DataHubContext
from datahub_agent_context.mcp_tools import (
    get_entities,
    get_lineage,
    grep_documents,
    list_schema_fields,
    save_document,
    search,
    search_documents,
)

from .models import GraphEdge, GraphNode, ImpactAssessment, Owner

DEFAULT_ASSET_URN = (
    "urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.ORDER_ENTRY_DB.analytics.order_details,PROD)"
)
DEFAULT_ASSET_NAME = "analytics.order_details"
DEFAULT_COLUMN = "discount_amount"
SAFE_CUSTOM_PROPERTIES = {
    "business_critical",
    "contains_pii",
    "materialization",
    "model_maturity",
}
SAFE_STRUCTURED_PROPERTIES = {
    "Cost Center",
    "Data Freshness SLA",
    "Data Quality Score",
    "Retention Period",
}
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
WRITE_BACK_VERIFY_ATTEMPTS = 4
WRITE_BACK_VERIFY_DELAY_SECONDS = 0.25
MAX_ASSET_SEARCH_RESULTS = 20
MAX_LINEAGE_ASSETS = 10
MAX_OWNERS_PER_ENTITY = 10
MAX_GOVERNANCE_NAMES = 20
MAX_RELATED_DOCUMENT_URNS = 100
MAX_PRIOR_INCIDENT_MEMORIES = 3
MAX_METADATA_SCAN_ITEMS = 100
CONTEXTLOOP_DOCUMENT_URN_PATTERN = re.compile(
    r"urn:li:document:shared-contextloop-[0-9a-f]{32}"
)
SAVE_DOCUMENT_RESTRICT_UPDATES_ENV = "SAVE_DOCUMENT_RESTRICT_UPDATES"
_SAVE_DOCUMENT_ENV_LOCK = Lock()


class DataHubWriteBackError(RuntimeError):
    """Raised when a DataHub document write cannot be proven from persisted state."""


def _save_document_to_generated_target(*, document_urn: str, **kwargs: Any) -> Any:
    """Use Agent Context Kit's URN upsert only for a server-generated document target.

    Agent Context Kit 1.6.0 supports a supplied URN, but its default hierarchy preflight treats
    the SDK's not-found exception as a hard failure instead of allowing the documented first
    upsert. ContextLoop already constrains the target and all content server-side, so the SDK
    restriction is disabled only while this serialized call executes and is then restored.
    """
    if CONTEXTLOOP_DOCUMENT_URN_PATTERN.fullmatch(document_urn) is None:
        raise DataHubWriteBackError("The approved ContextLoop document target is invalid.")

    with _SAVE_DOCUMENT_ENV_LOCK:
        previous = os.environ.get(SAVE_DOCUMENT_RESTRICT_UPDATES_ENV)
        os.environ[SAVE_DOCUMENT_RESTRICT_UPDATES_ENV] = "false"
        try:
            return save_document(urn=document_urn, **kwargs)
        finally:
            if previous is None:
                os.environ.pop(SAVE_DOCUMENT_RESTRICT_UPDATES_ENV, None)
            else:
                os.environ[SAVE_DOCUMENT_RESTRICT_UPDATES_ENV] = previous


def _document_urn_from_save_result(result: Any) -> str:
    if not isinstance(result, dict) or result.get("success") is not True:
        raise DataHubWriteBackError("save_document did not report a successful write.")
    candidate = result.get("urn") or result.get("document_urn")
    if not isinstance(candidate, str) or candidate != candidate.strip():
        raise DataHubWriteBackError("save_document did not return a valid document URN.")
    try:
        document_urn = DocumentUrn.from_string(candidate)
    except Exception as error:  # noqa: BLE001 - normalize SDK URN parser failures
        raise DataHubWriteBackError(
            "save_document did not return a valid document URN."
        ) from error
    return str(document_urn)


def _verify_exact_urns(*, actual: list[str] | None, expected: list[str], label: str) -> None:
    actual_urns = list(actual or [])
    if len(actual_urns) != len(expected) or set(actual_urns) != set(expected):
        raise DataHubWriteBackError(f"Persisted document {label} did not match the write request.")


def _verify_saved_document(
    document: Any,
    *,
    document_urn: str,
    title: str,
    content: str,
    related_asset_urns: list[str],
    related_document_urns: list[str],
) -> None:
    if not isinstance(document, Document) or str(document.urn) != document_urn:
        raise DataHubWriteBackError("The persisted entity was not the requested document.")
    if document.subtype != "Analysis":
        raise DataHubWriteBackError("The persisted document subtype was not Analysis.")
    if document.status != "PUBLISHED":
        raise DataHubWriteBackError("The persisted document status was not PUBLISHED.")
    _verify_exact_urns(
        actual=document.related_assets,
        expected=related_asset_urns,
        label="related assets",
    )
    _verify_exact_urns(
        actual=document.related_documents,
        expected=related_document_urns,
        label="related documents",
    )
    if document.title != title:
        raise DataHubWriteBackError("The persisted document title did not match the write request.")
    if document.text != content:
        raise DataHubWriteBackError(
            "The persisted document content did not match the write request."
        )


def _display_name(entity: dict[str, Any]) -> str:
    properties = entity.get("properties") or {}
    name = properties.get("name") or entity.get("name")
    return _clean_text(str(name), 200) if name else str(entity.get("urn") or "unknown")


def _platform(entity: dict[str, Any]) -> str:
    platform = entity.get("platform") or {}
    return (platform.get("name") or platform.get("urn", "unknown").split(":")[-1]).lower()


def _owners(entity: dict[str, Any]) -> list[Owner]:
    output: list[Owner] = []
    seen: set[str] = set()
    for entry in (entity.get("ownership") or {}).get("owners", [])[:MAX_METADATA_SCAN_ITEMS]:
        owner = entry.get("owner") or {}
        properties = owner.get("properties") or owner.get("info") or {}
        name = properties.get("displayName") or owner.get("name")
        if not name or name in seen:
            continue
        name = _clean_text(str(name), 160)
        if not name or name in seen:
            continue
        seen.add(name)
        ownership_type = (entry.get("ownershipType") or {}).get("info") or {}
        role = _clean_text(str(ownership_type.get("name") or "Owner"), 80)
        output.append(Owner(name=name, role=role))
        if len(output) >= MAX_OWNERS_PER_ENTITY:
            break
    return output


def _alias_node_owners(nodes: list[GraphNode]) -> list[GraphNode]:
    """Replace catalog display names and roles with stable response-local aliases."""
    owner_names = sorted({owner.name for node in nodes for owner in node.owners})
    aliases = {
        owner_name: f"Catalog owner {index:02d}"
        for index, owner_name in enumerate(owner_names, start=1)
    }
    return [
        node.model_copy(
            update={
                "owners": [
                    Owner(name=aliases[owner.name], role="Catalog owner")
                    for owner in node.owners
                ]
            }
        )
        for node in nodes
    ]


def _search_query(value: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9]+", value)
    return "/q " + "+".join(tokens)


def _clean_text(value: str, limit: int) -> str:
    scrubbed = EMAIL_PATTERN.sub("[redacted-email]", value)
    return re.sub(r"\s+", " ", scrubbed).strip()[:limit]


def _name_list(container: dict[str, Any], collection: str, item_key: str) -> list[str]:
    output: list[str] = []
    for entry in container.get(collection, [])[:MAX_METADATA_SCAN_ITEMS]:
        item = entry.get(item_key) or {}
        properties = item.get("properties") or {}
        name = _clean_text(
            str(properties.get("name") or item.get("urn", "").rsplit(":", 1)[-1]),
            120,
        )
        if name and name not in output:
            output.append(name)
        if len(output) >= MAX_GOVERNANCE_NAMES:
            break
    return output


def _governance_context(entity: dict[str, Any]) -> dict[str, Any]:
    properties = entity.get("properties") or {}
    editable = entity.get("editableProperties") or {}
    description = _clean_text(
        editable.get("description") or properties.get("description") or "",
        520,
    )
    tags = _name_list(entity.get("tags") or {}, "tags", "tag")
    terms = _name_list(entity.get("glossaryTerms") or {}, "terms", "term")
    domain = ((entity.get("domain") or {}).get("domain") or {}).get("properties") or {}
    domain_name = _clean_text(str(domain.get("name") or ""), 120) or None

    custom_properties: dict[str, str] = {}
    for item in properties.get("customProperties", [])[:MAX_METADATA_SCAN_ITEMS]:
        key = item.get("key")
        value = item.get("value")
        if key in SAFE_CUSTOM_PROPERTIES and value is not None:
            custom_properties[key] = _clean_text(str(value), 160)
        if len(custom_properties) >= len(SAFE_CUSTOM_PROPERTIES):
            break
    structured_properties: dict[str, str | int | float] = {}
    structured_items = (entity.get("structuredProperties") or {}).get("properties", [])
    for item in structured_items[:MAX_METADATA_SCAN_ITEMS]:
        definition = (item.get("structuredProperty") or {}).get("definition") or {}
        display_name = definition.get("displayName")
        if display_name not in SAFE_STRUCTURED_PROPERTIES:
            continue
        for value in item.get("values", []):
            candidate = value.get("stringValue", value.get("numberValue"))
            if candidate is None or (isinstance(candidate, str) and "@" in candidate):
                continue
            structured_properties[display_name] = (
                _clean_text(candidate, 160) if isinstance(candidate, str) else candidate
            )
            break
        if len(structured_properties) >= len(SAFE_STRUCTURED_PROPERTIES):
            break

    signal_labels = [
        *[f"tag: {name}" for name in tags],
        *[f"term: {name}" for name in terms],
    ]
    if domain_name:
        signal_labels.append(f"domain: {domain_name}")
    signal_labels.extend(f"{key}: {value}" for key, value in custom_properties.items())
    signal_labels.extend(f"{key}: {value}" for key, value in structured_properties.items())
    return {
        "description": description,
        "tags": tags,
        "glossary_terms": terms,
        "domain": domain_name,
        "custom_properties": custom_properties,
        "structured_properties": structured_properties,
        "signal_labels": signal_labels[:MAX_GOVERNANCE_NAMES],
    }


def _related_document_urns(entity: dict[str, Any]) -> set[str]:
    urns: set[str] = set()
    related_documents = (entity.get("relatedDocuments") or {}).get("documents", [])
    for item in related_documents[:MAX_METADATA_SCAN_ITEMS]:
        urn = item.get("urn")
        if urn:
            urns.add(urn)
        if len(urns) >= MAX_RELATED_DOCUMENT_URNS:
            break
    return urns


def _prior_incident_memories(entity: dict[str, Any], column: str) -> list[dict[str, str]]:
    related_urns = _related_document_urns(entity)
    if not related_urns:
        return []
    results = search_documents(
        query=_search_query(f"ContextLoop {column}"),
        num_results=10,
    )
    candidates: list[dict[str, str]] = []
    for result in results.get("searchResults", [])[:10]:
        document = result.get("entity") or {}
        urn = document.get("urn")
        title = (document.get("info") or {}).get("title") or ""
        if urn in related_urns and title.startswith("ContextLoop "):
            candidates.append({"urn": urn, "title": _clean_text(title, 220)})
    candidates = candidates[:MAX_PRIOR_INCIDENT_MEMORIES]
    if not candidates:
        return []

    excerpts = grep_documents(
        [item["urn"] for item in candidates],
        pattern=f"(?i){re.escape(column)}|recommended actions",
        context_chars=320,
        max_matches_per_doc=1,
    )
    excerpt_by_urn = {
        item.get("urn"): _clean_text(
            ((item.get("matches") or [{}])[0]).get("excerpt") or "",
            520,
        )
        for item in excerpts.get("results", [])[:MAX_PRIOR_INCIDENT_MEMORIES]
        if item.get("urn")
    }
    return [
        {**item, "excerpt": excerpt_by_urn.get(item["urn"], "")}
        for item in candidates
    ]


class DataHubService:
    def _client(self) -> DataHubClient:
        return DataHubClient.from_env()

    def health(self) -> tuple[bool, str]:
        try:
            with DataHubContext(self._client()):
                result = search(
                    query="/q order+details",
                    filter="entity_type = dataset",
                    num_results=1,
                )
            return bool(result.get("searchResults")), "DataHub OSS connected"
        except Exception as error:  # noqa: BLE001 - surface a safe connectivity summary
            return False, f"DataHub unavailable: {type(error).__name__}"

    def collect_context(
        self, *, asset_urn: str, asset_name: str, column: str, change_type: str, environment: str
    ) -> tuple[dict[str, Any], GraphNode, list[GraphNode], list[GraphEdge], list[int]]:
        try:
            parsed_asset_urn = DatasetUrn.from_string(asset_urn)
        except Exception as error:  # noqa: BLE001 - normalize SDK URN parser failures
            raise ValueError("The selected asset is not a valid DataHub dataset URN.") from error
        canonical_asset_name = parsed_asset_urn.name
        canonical_environment = parsed_asset_urn.env
        stage_started = time.perf_counter()
        with DataHubContext(self._client()):
            asset_search = search(
                query=_search_query(asset_name),
                filter="entity_type = dataset",
                num_results=20,
            )
            searched_urns = {
                (result.get("entity") or {}).get("urn")
                for result in asset_search.get("searchResults", [])[:MAX_ASSET_SEARCH_RESULTS]
            }
            if asset_urn not in searched_urns:
                raise ValueError("The selected asset could not be verified through DataHub search.")
            fields = list_schema_fields(urn=asset_urn, keywords=[column], limit=20)
            read_ms = int((time.perf_counter() - stage_started) * 1000)
            matching_fields = [
                field.get("fieldPath")
                for field in fields.get("fields", [])[:MAX_ASSET_SEARCH_RESULTS]
                if field.get("fieldPath") == column
            ]
            if not matching_fields:
                raise ValueError(
                    "The requested column is not present on the selected DataHub asset."
                )

            lineage_started = time.perf_counter()
            lineage = get_lineage(
                urn=asset_urn,
                column=column,
                upstream=False,
                max_hops=3,
                max_results=20,
            )
            raw_downstream_results = (lineage.get("downstreams") or {}).get(
                "searchResults", []
            )
            downstream_results: list[dict[str, Any]] = []
            seen_downstream_urns = {asset_urn}
            for result in raw_downstream_results[:MAX_ASSET_SEARCH_RESULTS]:
                urn = result.get("entity", {}).get("urn")
                if not urn or urn in seen_downstream_urns:
                    continue
                seen_downstream_urns.add(urn)
                downstream_results.append(result)
                if len(downstream_results) >= MAX_LINEAGE_ASSETS:
                    break
            downstream_urns = [result["entity"]["urn"] for result in downstream_results]
            all_urns = [asset_urn, *downstream_urns]
            details = get_entities(all_urns)
            detail_by_urn = {
                entity.get("urn"): entity
                for entity in details[: len(all_urns)]
                if entity.get("urn")
            }
            root_entity = detail_by_urn.get(asset_urn) or {
                "urn": asset_urn,
                "name": canonical_asset_name,
                "platform": {"name": "dbt"},
            }
            prior_incident_memories = _prior_incident_memories(root_entity, column)
            trace_ms = int((time.perf_counter() - lineage_started) * 1000)

        governance = _governance_context(root_entity)
        source_node = GraphNode(
            id="source",
            urn=asset_urn,
            name=canonical_asset_name,
            platform=_platform(root_entity),
            column=column,
            selected=True,
            owners=_owners(root_entity),
        )

        nodes: list[GraphNode] = [source_node]
        edges: list[GraphEdge] = []
        for index, result in enumerate(downstream_results, start=1):
            summary = result.get("entity") or {}
            urn = summary.get("urn")
            if not urn:
                continue
            entity = detail_by_urn.get(urn) or summary
            node = GraphNode(
                id=f"downstream-{index}",
                urn=urn,
                name=_display_name(entity),
                platform=_platform(entity),
                column=column,
                owners=_owners(entity),
            )
            nodes.append(node)
            edges.append(GraphEdge(source="source", target=node.id, kind="downstream"))

        nodes = _alias_node_owners(nodes)
        source_node = nodes[0]

        owner_names: list[str] = []
        for node in nodes:
            owner_names.extend(owner.name for owner in node.owners)
        owner_names = list(dict.fromkeys(owner_names))
        bi_platforms = {"powerbi", "looker", "tableau", "superset", "mode"}
        business_reporting_asset_count = sum(
            1 for node in nodes[1:] if node.platform in bi_platforms
        )
        context = {
            "change": {
                "asset_urn": asset_urn,
                "asset_name": canonical_asset_name,
                "column": column,
                "change_type": change_type,
                "environment": canonical_environment,
            },
            "schema_match": matching_fields,
            "asset_search_verified": True,
            "source": source_node.model_dump(),
            "downstream_assets": [node.model_dump() for node in nodes[1:]],
            "owner_names": owner_names,
            "business_reporting_asset_count": business_reporting_asset_count,
            "lineage_total": (lineage.get("downstreams") or {}).get("total", len(nodes) - 1),
            "governance": governance,
            "governance_signal_count": len(governance["signal_labels"]),
            "prior_incident_memories": prior_incident_memories,
        }
        return context, source_node, nodes, edges, [read_ms, trace_ms]

    def save_incident_memory(
        self,
        *,
        run_id: str,
        document_urn: str,
        reviewed_at: datetime,
        source_asset_urn: str,
        related_asset_urns: list[str],
        related_document_urns: list[str],
        column: str,
        change_type: str,
        impact: ImpactAssessment,
    ) -> tuple[str, str]:
        approved_document_urn = str(DocumentUrn.from_string(document_urn))
        title = f"ContextLoop {run_id}: {impact.headline}"
        actions = "\n".join(
            f"{action.id}. **{action.title}** — Owner: {action.owner}" for action in impact.actions
        )
        evidence = "\n".join(f"- {item}" for item in impact.evidence)
        content = f"""# {title}

## Proposed change

- Change: `{change_type}`
- Column: `{column}`
- Source: `{source_asset_urn}`
- Severity: **{impact.severity}**

## Impact

{impact.why_it_matters}

Affected assets: **{impact.affected_asset_count}**<br>
Owners involved: **{impact.owner_count}**<br>
Business reporting assets: **{impact.business_reporting_asset_count}**
Prior incident memories linked: **{len(related_document_urns)}**

## Evidence from DataHub

{evidence}

## Recommended actions

{actions}

---
Generated by ContextLoop from DataHub Agent Context Kit metadata.
Reviewed through the explicit write-back approval step at {reviewed_at.isoformat()}.
"""
        related = list(dict.fromkeys([source_asset_urn, *related_asset_urns]))
        related_documents = list(dict.fromkeys(related_document_urns))
        client = self._client()
        with DataHubContext(client):
            result = _save_document_to_generated_target(
                document_urn=approved_document_urn,
                document_type="Analysis",
                title=title,
                content=content,
                topics=["schema-change", "impact-analysis", "incident-memory"],
                related_assets=related,
                related_documents=related_documents or None,
            )
        document_urn = _document_urn_from_save_result(result)
        if document_urn != approved_document_urn:
            raise DataHubWriteBackError(
                "DataHub returned a different document target than the approved write request."
            )

        last_error: Exception | None = None
        for attempt in range(WRITE_BACK_VERIFY_ATTEMPTS):
            try:
                saved_document = client.entities.get(document_urn)
                _verify_saved_document(
                    saved_document,
                    document_urn=document_urn,
                    title=title,
                    content=content,
                    related_asset_urns=related,
                    related_document_urns=related_documents,
                )
                return document_urn, title
            except Exception as error:  # noqa: BLE001 - retry SDK reads and aspect propagation
                last_error = error
                if attempt + 1 < WRITE_BACK_VERIFY_ATTEMPTS:
                    time.sleep(WRITE_BACK_VERIFY_DELAY_SECONDS)
        if isinstance(last_error, DataHubWriteBackError):
            raise last_error
        raise DataHubWriteBackError(
            "The persisted document could not be re-read through the DataHub SDK."
        ) from last_error
