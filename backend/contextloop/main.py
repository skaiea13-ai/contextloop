from __future__ import annotations

import asyncio
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from secrets import compare_digest, token_hex
from threading import BoundedSemaphore, Lock
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
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

LOCAL_SESSION_HEADER = "X-ContextLoop-Token"
MIN_LOCAL_SESSION_TOKEN_LENGTH = 32


def require_local_session(
    supplied_token: str | None = Header(default=None, alias=LOCAL_SESSION_HEADER),
) -> None:
    expected_token = os.getenv("CONTEXTLOOP_LOCAL_TOKEN", "")
    if len(expected_token) < MIN_LOCAL_SESSION_TOKEN_LENGTH:
        raise HTTPException(
            status_code=503,
            detail="The local session gate is not configured.",
        )
    if supplied_token is None or not compare_digest(supplied_token, expected_token):
        raise HTTPException(
            status_code=401,
            detail="A valid local session token is required.",
        )


LOCAL_SESSION_DEPENDENCIES = [Depends(require_local_session)]


app = FastAPI(title="ContextLoop", version="0.1.0")
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1"],
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", LOCAL_SESSION_HEADER],
)

datahub = DataHubService()
codex = CodexAuthRunner()
analysis_slot = BoundedSemaphore(value=1)
write_back_slot = BoundedSemaphore(value=1)
pending_write_backs: dict[str, PendingWriteBack] = {}
in_flight_write_backs: dict[str, PendingWriteBack] = {}
completed_write_backs: dict[str, tuple[str, WriteBackResponse]] = {}
write_back_state_lock = Lock()
MAX_PENDING_WRITE_BACKS = 50
MAX_COMPLETED_WRITE_BACKS = 50


def fixture_enabled() -> bool:
    return os.getenv("CONTEXTLOOP_FAKE_CODEX") == "1"


async def codex_status() -> tuple[bool, str, str]:
    if fixture_enabled():
        return True, "Deterministic fixture enabled; no model call", "deterministic_fixture"
    ok, detail = await asyncio.to_thread(codex.auth_status)
    return ok, detail, "chatgpt_oauth"


def _run_analysis_with_reserved_slot(request: AnalyzeRequest):
    """Run both blocking integrations while retaining the single analysis slot."""
    try:
        context, source, nodes, edges, datahub_timings = datahub.collect_context(
            asset_urn=request.asset_urn,
            asset_name=request.asset_name,
            column=request.column,
            change_type=request.change_type,
            environment=request.environment,
        )
        reason_started = time.perf_counter()
        impact, auth_mode = codex.analyze(context)
        reason_ms = int((time.perf_counter() - reason_started) * 1000)
        return context, source, nodes, edges, datahub_timings, impact, auth_mode, reason_ms
    finally:
        analysis_slot.release()


def _run_write_back_with_claim(
    write_back_token: str,
    pending: PendingWriteBack,
) -> WriteBackResponse:
    """Finish the claimed mutation even if the requesting client disconnects."""
    try:
        try:
            document_urn, title = datahub.save_incident_memory(
                run_id=pending.run_id,
                document_urn=pending.document_urn,
                reviewed_at=pending.reviewed_at,
                source_asset_urn=pending.source_asset_urn,
                related_asset_urns=pending.related_asset_urns,
                related_document_urns=pending.related_document_urns,
                column=pending.column,
                change_type=pending.change_type,
                impact=pending.impact,
            )
        except Exception:  # noqa: BLE001 - restore the exact claim before translation
            with write_back_state_lock:
                in_flight_write_backs.pop(write_back_token, None)
                pending_write_backs[write_back_token] = pending
                while len(pending_write_backs) > MAX_PENDING_WRITE_BACKS:
                    pending_write_backs.pop(next(iter(pending_write_backs)))
            raise

        response = WriteBackResponse(
            document_urn=document_urn,
            title=title,
            datahub_url="http://localhost:9002/document/" + document_urn,
            saved_at=datetime.now(UTC),
        )
        with write_back_state_lock:
            in_flight_write_backs.pop(write_back_token, None)
            completed_write_backs[write_back_token] = (pending.run_id, response)
            while len(completed_write_backs) > MAX_COMPLETED_WRITE_BACKS:
                completed_write_backs.pop(next(iter(completed_write_backs)))
        return response
    finally:
        write_back_slot.release()


@app.get("/api/health", dependencies=LOCAL_SESSION_DEPENDENCIES)
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


@app.get(
    "/api/bootstrap",
    response_model=BootstrapResponse,
    dependencies=LOCAL_SESSION_DEPENDENCIES,
)
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


@app.post(
    "/api/analyze",
    response_model=AnalysisResponse,
    dependencies=LOCAL_SESSION_DEPENDENCIES,
)
async def analyze(request: AnalyzeRequest) -> AnalysisResponse:
    if not analysis_slot.acquire(blocking=False):
        raise HTTPException(
            status_code=429,
            detail="Another impact analysis is already running for this local session.",
        )
    try:
        (
            context,
            source,
            nodes,
            edges,
            datahub_timings,
            impact,
            auth_mode,
            reason_ms,
        ) = await asyncio.to_thread(
            _run_analysis_with_reserved_slot,
            request,
        )
    except CodexAuthError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:  # noqa: BLE001 - translate integration failures to a safe API error
        raise HTTPException(
            status_code=502,
            detail=f"Impact analysis failed: {type(error).__name__}",
        ) from error

    analysis_id = uuid4().hex
    run_id = f"CL-{analysis_id[:4].upper()}"
    write_back_token = token_hex(32)
    pending = PendingWriteBack(
        run_id=run_id,
        document_urn=f"urn:li:document:shared-contextloop-{analysis_id}",
        source_asset_urn=source.urn,
        related_asset_urns=[node.urn for node in nodes[1:]],
        related_document_urns=[
            memory["urn"] for memory in context["prior_incident_memories"]
        ],
        column=request.column,
        change_type=request.change_type,
        impact=impact,
    )
    with write_back_state_lock:
        while (
            write_back_token in pending_write_backs
            or write_back_token in in_flight_write_backs
            or write_back_token in completed_write_backs
        ):
            write_back_token = token_hex(32)
        pending_write_backs[write_back_token] = pending
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
        write_back_token=write_back_token,
        created_at=datetime.now(UTC),
        source_asset=source,
        nodes=nodes,
        edges=edges,
        impact=impact,
        timings=timings,
        model=codex.model,
        auth_mode=auth_mode,
    )


@app.post(
    "/api/write-back",
    response_model=WriteBackResponse,
    dependencies=LOCAL_SESSION_DEPENDENCIES,
)
async def write_back(request: WriteBackRequest) -> WriteBackResponse:
    with write_back_state_lock:
        completed = completed_write_backs.get(request.write_back_token)
        if completed is not None:
            completed_run_id, response = completed
            if completed_run_id != request.run_id:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        "No pending grounded analysis exists for this run. "
                        "Run the impact loop again."
                    ),
                )
            return response

        in_flight = in_flight_write_backs.get(request.write_back_token)
        if in_flight is not None:
            if in_flight.run_id != request.run_id:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        "No pending grounded analysis exists for this run. "
                        "Run the impact loop again."
                    ),
                )
            raise HTTPException(
                status_code=409,
                detail="This approved DataHub write-back is already in progress.",
            )

        pending = pending_write_backs.get(request.write_back_token)
        if pending is None or pending.run_id != request.run_id:
            raise HTTPException(
                status_code=404,
                detail=(
                    "No pending grounded analysis exists for this run. "
                    "Run the impact loop again."
                ),
            )
        pending = pending.model_copy(
            update={"reviewed_at": pending.reviewed_at or datetime.now(UTC)}
        )
        if not write_back_slot.acquire(blocking=False):
            raise HTTPException(
                status_code=429,
                detail="Another DataHub write-back is already running for this local session.",
            )
        pending_write_backs.pop(request.write_back_token)
        in_flight_write_backs[request.write_back_token] = pending

    try:
        return await asyncio.to_thread(
            _run_write_back_with_claim,
            request.write_back_token,
            pending,
        )
    except Exception as error:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=(
                "DataHub write-back could not be verified. "
                "The pending analysis was preserved."
            ),
        ) from error


frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
