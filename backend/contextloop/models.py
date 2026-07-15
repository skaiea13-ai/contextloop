from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

ChangeType = Literal["drop_column", "modify_column", "add_column"]
Environment = Literal["PROD", "STG", "DEV"]
Headline = Annotated[str, Field(min_length=1, max_length=180)]
SummaryText = Annotated[str, Field(min_length=1, max_length=400)]
ExplanationText = Annotated[str, Field(min_length=1, max_length=800)]
ActionText = Annotated[str, Field(min_length=1, max_length=240)]
EvidenceText = Annotated[str, Field(min_length=1, max_length=280)]


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_urn: str = Field(min_length=10, max_length=500)
    asset_name: str = Field(default="analytics.order_details", min_length=1, max_length=200)
    column: str = Field(default="discount_amount", min_length=1, max_length=200)
    change_type: ChangeType = "drop_column"
    environment: Environment = "PROD"


class Owner(BaseModel):
    name: str
    role: str = "Owner"


class GraphNode(BaseModel):
    id: str
    urn: str
    name: str
    platform: str
    entity_type: str = "dataset"
    column: str | None = None
    selected: bool = False
    owners: list[Owner] = Field(default_factory=list)


class GraphEdge(BaseModel):
    source: str
    target: str
    kind: Literal["selected", "downstream"] = "downstream"


class ImpactAction(BaseModel):
    id: int
    title: ActionText
    owner: Annotated[str, Field(min_length=1, max_length=160)]
    priority: Literal["now", "next", "monitor"] = "now"


class ImpactAssessment(BaseModel):
    severity: Literal["P0", "P1", "P2", "P3"]
    headline: Headline
    summary: SummaryText
    why_it_matters: ExplanationText
    affected_asset_count: int
    owner_count: int
    business_reporting_asset_count: int
    evidence: list[EvidenceText] = Field(min_length=2, max_length=5)
    actions: list[ImpactAction] = Field(min_length=3, max_length=5)


class AgentTiming(BaseModel):
    stage: Literal["read", "trace", "reason", "prepare", "write"]
    label: str
    detail: str
    elapsed_ms: int
    status: Literal["complete", "waiting"] = "complete"


class AnalysisResponse(BaseModel):
    run_id: str
    created_at: datetime
    source_asset: GraphNode
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    impact: ImpactAssessment
    timings: list[AgentTiming]
    model: str
    auth_mode: Literal["chatgpt_oauth", "fixture"]


class WriteBackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    approved: Literal[True]


class PendingWriteBack(BaseModel):
    source_asset_urn: str
    related_asset_urns: list[str]
    related_document_urns: list[str]
    column: str
    change_type: ChangeType
    impact: ImpactAssessment


class WriteBackResponse(BaseModel):
    document_urn: str
    title: str
    datahub_url: str
    saved_at: datetime


class ServiceStatus(BaseModel):
    ok: bool
    label: str
    detail: str


class BootstrapResponse(BaseModel):
    datahub: ServiceStatus
    codex: ServiceStatus
    default_asset_urn: str
    default_asset_name: str
    default_column: str
    datahub_version: str
    model: str
    execution_mode: Literal["chatgpt_oauth", "deterministic_fixture"]
