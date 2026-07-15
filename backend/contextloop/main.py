from __future__ import annotations

import asyncio
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .codex_auth import CodexAuthError, CodexAuthRunner
from .datahub_service import (
    DEFAULT_ASSET_NAME,
    DEFAULT_ASSET_URN,
    DEFAULT_COLUMN,
    DataHubService,
)
from .models import (
    AgentTiming,
    AnalysisResponse,
    AnalyzeRequest,
    BootstrapResponse,
    PendingWriteBack,
    ServiceStatus,
    WriteBackRequest,
    WriteBackResponse,
)

app = FastAPI(title="ContextLoop", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

datahub = DataHubService()
codex = CodexAuthRunner()
pending_write_backs: dict[str, PendingWriteBack] = {}
MAX_PENDING_WRITE_BACKS = 50


def fixture_enabled() -> bool:
    return os.getenv("CONTEXTLOOP_FAKE_CODEX") == "1"


async def codex_status() -> tuple[bool, str, str]:
    if fixture_enabled():
        return True, "Deterministic fixture enabled; no model call", "deterministic_fixture"
    ok, detail = await asyncio.to_thread(codex.auth_status)
    return ok, detail, "chatgpt_oauth"


@app.get("/api/health")
async def health() -> dict[str, object]:
    datahub_ok, datahub_detail = await asyncio.to_thread(datahub.health)
    codex_ok, codex_detail, execution_mode = await codex_status()
    return {
        "ok": datahub_ok and codex_ok,
        "datahub": {"ok": datahub_ok, "detail": datahub_detail},
        "codex": {"ok": codex_ok, "detail": codex_detail},
        "auth_mode": (
            "Deterministic fixture (no model call)"
            if execution_mode == "deterministic_fixture"
            else "ChatGPT OAuth"
        ),
        "api_key_required": False,
    }


@app.get("/api/bootstrap", response_model=BootstrapResponse)
async def bootstrap() -> BootstrapResponse:
    datahub_ok, datahub_detail = await asyncio.to_thread(datahub.health)
    codex_ok, codex_detail, execution_mode = await codex_status()
    return BootstrapResponse(
        datahub=ServiceStatus(ok=datahub_ok, label="DataHub OSS", detail=datahub_detail),
        codex=ServiceStatus(ok=codex_ok, label="Codex Auth", detail=codex_detail),
        default_asset_urn=DEFAULT_ASSET_URN,
        default_asset_name=DEFAULT_ASSET_NAME,
        default_column=DEFAULT_COLUMN,
        datahub_version="1.6.0",
        model=codex.model if execution_mode == "chatgpt_oauth" else "deterministic fixture",
        execution_mode=execution_mode,
    )


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalyzeRequest) -> AnalysisResponse:
    try:
        context, source, nodes, edges, datahub_timings = await asyncio.to_thread(
            datahub.collect_context,
            asset_urn=request.asset_urn,
            asset_name=request.asset_name,
            column=request.column,
            change_type=request.change_type,
            environment=request.environment,
        )
        reason_started = time.perf_counter()
        impact, auth_mode = await asyncio.to_thread(codex.analyze, context)
        reason_ms = int((time.perf_counter() - reason_started) * 1000)
    except CodexAuthError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:  # noqa: BLE001 - translate integration failures to a safe API error
        raise HTTPException(
            status_code=502,
            detail=f"Impact analysis failed: {type(error).__name__}",
        ) from error

    run_id = f"CL-{uuid4().hex[:4].upper()}"
    pending_write_backs[run_id] = PendingWriteBack(
        source_asset_urn=source.urn,
        related_asset_urns=[node.urn for node in nodes[1:]],
        related_document_urns=[
            memory["urn"] for memory in context["prior_incident_memories"]
        ],
        column=request.column,
        change_type=request.change_type,
        impact=impact,
    )
    while len(pending_write_backs) > MAX_PENDING_WRITE_BACKS:
        pending_write_backs.pop(next(iter(pending_write_backs)))
    timings = [
        AgentTiming(
            stage="read",
            label="Read context",
            detail=(
                "Verified the asset through DataHub search; loaded schema, "
                f"{context['governance_signal_count']} governance signals, and "
                f"{len(context['prior_incident_memories'])} prior incident memories."
            ),
            elapsed_ms=datahub_timings[0],
        ),
        AgentTiming(
            stage="trace",
            label="Query lineage",
            detail=(
                "Queried column-level lineage and projected "
                f"{len(nodes) - 1} downstream assets."
            ),
            elapsed_ms=datahub_timings[1],
        ),
        AgentTiming(
            stage="reason",
            label="Reason",
            detail=(
                "Classified severity and bounded risk factors with the "
                "ChatGPT-authenticated Codex runtime."
            ),
            elapsed_ms=reason_ms,
        ),
        AgentTiming(
            stage="prepare",
            label="Prepare actions",
            detail=f"Prepared {len(impact.actions)} grounded remediation actions.",
            elapsed_ms=0,
        ),
        AgentTiming(
            stage="write",
            label="Write back",
            detail="Waiting for explicit approval before creating a DataHub context document.",
            elapsed_ms=0,
            status="waiting",
        ),
    ]
    return AnalysisResponse(
        run_id=run_id,
        created_at=datetime.now(UTC),
        source_asset=source,
        nodes=nodes,
        edges=edges,
        impact=impact,
        timings=timings,
        model=codex.model,
        auth_mode=auth_mode,
    )


@app.post("/api/write-back", response_model=WriteBackResponse)
async def write_back(request: WriteBackRequest) -> WriteBackResponse:
    pending = pending_write_backs.get(request.run_id)
    if pending is None:
        raise HTTPException(
            status_code=404,
            detail="No pending grounded analysis exists for this run. Run the impact loop again.",
        )
    try:
        document_urn, title = await asyncio.to_thread(
            datahub.save_incident_memory,
            run_id=request.run_id,
            source_asset_urn=pending.source_asset_urn,
            related_asset_urns=pending.related_asset_urns,
            related_document_urns=pending.related_document_urns,
            column=pending.column,
            change_type=pending.change_type,
            impact=pending.impact,
        )
    except Exception as error:  # noqa: BLE001
        pending_write_backs[request.run_id] = pending
        raise HTTPException(
            status_code=502,
            detail=(
                "DataHub write-back could not be verified. "
                "The pending analysis was preserved."
            ),
        ) from error
    pending_write_backs.pop(request.run_id, None)
    return WriteBackResponse(
        document_urn=document_urn,
        title=title,
        datahub_url="http://localhost:9002/document/" + document_urn,
        saved_at=datetime.now(UTC),
    )


frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
