from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from backend.contextloop.codex_auth import (
    OUTPUT_SCHEMA,
    CodexAuthError,
    CodexAuthRunner,
    oauth_only_environment,
)

SOURCE_URN = (
    "urn:li:dataset:(urn:li:dataPlatform:snowflake,warehouse.canonical_orders,DEV)"
)


def _context(*, owner_names: list[str] | None = None) -> dict[str, Any]:
    owners = ["Data Platform Team", "Julia Novak"] if owner_names is None else owner_names
    nested_owners = [{"name": owner, "role": "Owner"} for owner in owners]
    return {
        "change": {
            "asset_urn": SOURCE_URN,
            "asset_name": "request.supplied_alias",
            "column": "request_supplied_column",
            "change_type": "drop_column",
            "environment": "PROD",
        },
        "schema_match": ["discount_amount"],
        "asset_search_verified": True,
        "source": {
            "id": "source",
            "urn": SOURCE_URN,
            "name": "warehouse.canonical_orders",
            "platform": "snowflake",
            "column": "discount_amount",
            "selected": True,
            "owners": nested_owners[:1],
        },
        "downstream_assets": [
            {
                "id": "downstream-1",
                "urn": "urn:li:dashboard:(looker,revenue_overview)",
                "name": "Revenue Overview",
                "platform": "looker",
                "owners": nested_owners[:1],
            },
            {
                "id": "downstream-2",
                "urn": (
                    "urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.order_rollup,DEV)"
                ),
                "name": "analytics.order_rollup",
                "platform": "snowflake",
                "owners": nested_owners[1:2],
            },
        ],
        "owner_names": owners,
        # Deliberately inconsistent: the runner must recompute this from retrieved assets.
        "business_reporting_asset_count": 99,
        "governance": {"signal_labels": ["tag: Authoritative Source"]},
        "prior_incident_memories": [
            {"urn": "urn:li:document:prior", "title": "Prior incident"}
        ],
    }


def _model_output() -> dict[str, Any]:
    return {
        "severity": "P0",
        # unowned_dependencies is valid syntax but unsupported by this context.
        "risk_factors": ["reporting_disruption", "unowned_dependencies"],
    }


def test_oauth_environment_is_an_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-propagate")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "must-not-propagate")
    monkeypatch.setenv("CONTEXTLOOP_INTERNAL_SECRET", "must-not-propagate")
    monkeypatch.setenv("HOME", "/tmp/oauth-home")
    monkeypatch.setenv("CODEX_HOME", "/tmp/oauth-home/.codex")
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.invalid")

    child_environment = oauth_only_environment()

    assert child_environment["HOME"] == "/tmp/oauth-home"
    assert child_environment["CODEX_HOME"] == "/tmp/oauth-home/.codex"
    assert child_environment["HTTPS_PROXY"] == "http://proxy.invalid"
    assert "OPENAI_API_KEY" not in child_environment
    assert "AWS_SECRET_ACCESS_KEY" not in child_environment
    assert "CONTEXTLOOP_INTERNAL_SECRET" not in child_environment


def test_model_output_schema_has_no_free_text_fields() -> None:
    assert OUTPUT_SCHEMA["required"] == ["severity", "risk_factors"]
    assert set(OUTPUT_SCHEMA["properties"]) == {"severity", "risk_factors"}
    assert OUTPUT_SCHEMA["additionalProperties"] is False


def test_auth_status_runs_from_an_ephemeral_directory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = CodexAuthRunner()
    runner.executable = "/usr/local/bin/codex"
    captured_cwd: Path | None = None

    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        nonlocal captured_cwd
        captured_cwd = Path(kwargs["cwd"])
        assert captured_cwd.is_dir()
        assert command == [runner.executable, "login", "status"]
        assert "OPENAI_API_KEY" not in kwargs["env"]
        return subprocess.CompletedProcess(command, 0, "Logged in using ChatGPT\n", "")

    monkeypatch.setattr("backend.contextloop.codex_auth.subprocess.run", fake_run)

    assert runner.auth_status() == (True, "Logged in using ChatGPT")
    assert captured_cwd is not None
    assert not captured_cwd.exists()


def test_fixture_analysis_is_deterministic_and_grounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CONTEXTLOOP_FAKE_CODEX", "1")
    runner = CodexAuthRunner()

    impact, auth_mode = runner.analyze(_context())

    assert auth_mode == "fixture"
    assert impact.affected_asset_count == 2
    assert impact.business_reporting_asset_count == 1
    assert impact.owner_count == 2
    assert len(impact.evidence) == 5
    assert {action.owner for action in impact.actions} <= {
        "Data Platform Team",
        "Julia Novak",
    }
    assert "warehouse.canonical_orders" in impact.summary
    assert "DEV" in impact.summary
    assert "The retrieved lineage exposes 1 BI reporting asset" in impact.why_it_matters
    assert "request.supplied_alias" not in impact.model_dump_json()
    assert "request_supplied_column" not in impact.model_dump_json()


def test_empty_owner_names_are_explicitly_unassigned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CONTEXTLOOP_FAKE_CODEX", "1")
    runner = CodexAuthRunner()

    impact, _ = runner.analyze(_context(owner_names=[]))

    assert impact.owner_count == 0
    assert {action.owner for action in impact.actions} == {"Unassigned"}
    serialized = impact.model_dump_json()
    assert "Data Platform Team" not in serialized
    assert "Phantom Owner" not in serialized


def test_bounded_model_signals_are_grounded_and_tools_are_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = CodexAuthRunner()
    runner.executable = "/usr/local/bin/codex"
    monkeypatch.setattr(runner, "auth_status", lambda: (True, "Logged in using ChatGPT"))
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-propagate")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "must-not-propagate")
    captured: dict[str, Any] = {}

    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured["cwd"] = Path(kwargs["cwd"])
        captured["env"] = kwargs["env"]
        captured["prompt"] = kwargs["input"]
        assert captured["cwd"].is_dir()
        output_path = Path(command[command.index("--output-last-message") + 1])
        output_path.write_text(json.dumps(_model_output()), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("backend.contextloop.codex_auth.subprocess.run", fake_run)

    impact, auth_mode = runner.analyze(_context())

    assert auth_mode == "chatgpt_oauth"
    assert impact.severity == "P0"
    assert impact.affected_asset_count == 2
    assert impact.owner_count == 2
    assert impact.business_reporting_asset_count == 1
    assert {action.owner for action in impact.actions} <= {
        "Data Platform Team",
        "Julia Novak",
    }
    assert "BI reporting disruption" in impact.why_it_matters
    assert "unowned dependencies" not in impact.why_it_matters

    command = captured["command"]
    assert command[command.index("-C") + 1] == str(captured["cwd"])
    assert command.count("--disable") == 6
    for feature in ("shell_tool", "apps", "browser_use", "computer_use", "hooks", "plugins"):
        assert ["--disable", feature] == command[
            command.index(feature) - 1 : command.index(feature) + 1
        ]
    assert "OPENAI_API_KEY" not in captured["env"]
    assert "AWS_SECRET_ACCESS_KEY" not in captured["env"]
    assert not captured["cwd"].exists()

    prompt = captured["prompt"]
    assert '"asset_name": "warehouse.canonical_orders"' in prompt
    assert '"environment": "DEV"' in prompt
    assert '"column": "discount_amount"' in prompt
    assert "request.supplied_alias" not in prompt
    assert "request_supplied_column" not in prompt


def test_unexpected_model_free_text_is_rejected() -> None:
    runner = CodexAuthRunner()
    context = runner._grounded_context(_context())
    raw = {**_model_output(), "headline": "Phantom Asset owned by Phantom Owner"}

    with pytest.raises(CodexAuthError, match="unexpected fields"):
        runner._ground_assessment(raw, context)


def test_missing_canonical_source_metadata_fails_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CONTEXTLOOP_FAKE_CODEX", "1")
    context = _context()
    context["source"] = {}
    context["change"]["asset_urn"] = "not-a-datahub-dataset-urn"

    with pytest.raises(CodexAuthError, match="canonical source asset metadata"):
        CodexAuthRunner().analyze(context)
