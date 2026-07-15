#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PORT="${CONTEXTLOOP_RELEASE_PORT:-8010}"
BASE_URL="http://127.0.0.1:${PORT}"
TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/contextloop-release.XXXXXX")"
BACKEND_PID=""

cleanup() {
  if [[ -n "$BACKEND_PID" ]]; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
    wait "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
  rm -rf "$TEMP_DIR"
}
trap cleanup EXIT INT TERM

./scripts/verify.sh

if [[ "$(codex login status 2>&1)" != *"Logged in using ChatGPT"* ]]; then
  echo "Live verification requires Codex ChatGPT OAuth." >&2
  exit 1
fi
curl --fail --silent http://127.0.0.1:8080/health >/dev/null

env -u CONTEXTLOOP_FAKE_CODEX uv run uvicorn backend.contextloop.main:app \
  --host 127.0.0.1 --port "$PORT" >"$TEMP_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

backend_ready=0
for _ in {1..120}; do
  if ! kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    echo "Release backend exited before becoming ready." >&2
    sed -n '1,120p' "$TEMP_DIR/backend.log" >&2
    exit 1
  fi
  if curl --fail --silent "$BASE_URL/api/health" >"$TEMP_DIR/health.json"; then
    backend_ready=1
    break
  fi
  sleep 0.25
done

if [[ "$backend_ready" != "1" ]]; then
  echo "Release backend did not become ready within 30 seconds." >&2
  exit 1
fi

jq --exit-status '
  .ok == true and
  .datahub.ok == true and
  .codex.ok == true and
  .auth_mode == "ChatGPT OAuth" and
  .api_key_required == false
' "$TEMP_DIR/health.json" >/dev/null

jq --null-input '{
  asset_urn: "urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.ORDER_ENTRY_DB.analytics.order_details,PROD)",
  asset_name: "analytics.order_details",
  column: "discount_amount",
  change_type: "drop_column",
  environment: "PROD"
}' >"$TEMP_DIR/request.json"

curl --fail --silent --show-error \
  --request POST "$BASE_URL/api/analyze" \
  --header 'Content-Type: application/json' \
  --data-binary @"$TEMP_DIR/request.json" >"$TEMP_DIR/analysis.json"

jq --exit-status '
  ([.nodes[].owners[].name] | unique) as $catalog_owners |
  (
    .auth_mode == "chatgpt_oauth" and
    .impact.affected_asset_count == ((.nodes | length) - 1) and
    .impact.owner_count == ($catalog_owners | length) and
    .impact.business_reporting_asset_count >= 0 and
    (.impact.evidence | length) >= 2 and
    (.impact.actions | length) >= 3 and
    .timings[-1].status == "waiting" and
    ([.impact.actions[].owner] | all(. as $owner | $catalog_owners | index($owner) != null))
  )
' "$TEMP_DIR/analysis.json" >/dev/null

run_id="$(jq --raw-output '.run_id' "$TEMP_DIR/analysis.json")"
EXPECTED_RUN_ID="$run_id" uv run python - <<'PY'
import os

from datahub.sdk import DataHubClient
from datahub_agent_context import DataHubContext
from datahub_agent_context.mcp_tools import search_documents

run_id = os.environ["EXPECTED_RUN_ID"]
with DataHubContext(DataHubClient.from_env()):
    result = search_documents(query=run_id, num_results=10)
entries = [
    *(result.get("searchResults") or []),
    *(result.get("documents") or []),
]
for entry in entries:
    document = entry.get("entity") or entry
    title = (document.get("info") or {}).get("title") or document.get("title") or ""
    assert run_id not in title, "Document existed before explicit approval"
PY

jq --null-input --arg run_id "$run_id" '{run_id: $run_id, approved: true}' \
  >"$TEMP_DIR/writeback-request.json"

curl --fail --silent --show-error \
  --request POST "$BASE_URL/api/write-back" \
  --header 'Content-Type: application/json' \
  --data-binary @"$TEMP_DIR/writeback-request.json" >"$TEMP_DIR/writeback.json"

document_urn="$(jq --raw-output '.document_urn' "$TEMP_DIR/writeback.json")"
datahub_url="$(jq --raw-output '.datahub_url' "$TEMP_DIR/writeback.json")"
expected_datahub_url="http://localhost:9002/document/${document_urn}"
if [[ "$datahub_url" != "$expected_datahub_url" ]]; then
  echo "DataHub document URL does not preserve the full document URN." >&2
  exit 1
fi
expected_assets_json="$(jq --compact-output '[.nodes[].urn] | unique' "$TEMP_DIR/analysis.json")"

DOCUMENT_URN="$document_urn" \
EXPECTED_ASSETS_JSON="$expected_assets_json" \
EXPECTED_RUN_ID="$run_id" \
ANALYSIS_JSON_PATH="$TEMP_DIR/analysis.json" \
WRITEBACK_JSON_PATH="$TEMP_DIR/writeback.json" \
uv run python - <<'PY'
import json
import os
import re

from datahub.sdk import DataHubClient

urn = os.environ["DOCUMENT_URN"]
expected_assets = set(json.loads(os.environ["EXPECTED_ASSETS_JSON"]))
expected_run_id = os.environ["EXPECTED_RUN_ID"]
with open(os.environ["ANALYSIS_JSON_PATH"], encoding="utf-8") as handle:
    analysis = json.load(handle)
with open(os.environ["WRITEBACK_JSON_PATH"], encoding="utf-8") as handle:
    writeback = json.load(handle)
impact = analysis["impact"]
document = DataHubClient.from_env().entities.get(urn)
text = document.text or ""
related_documents = document.related_documents or []
prior_count = re.search(r"Prior incident memories linked: \*\*(\d+)\*\*", text)

assert str(document.urn) == urn
assert document.subtype == "Analysis"
assert document.status == "PUBLISHED"
assert document.title == writeback["title"]
assert document.title == f"ContextLoop {expected_run_id}: {impact['headline']}"
assert f"- Severity: **{impact['severity']}**" in text
assert f"Affected assets: **{impact['affected_asset_count']}**" in text
assert f"Owners involved: **{impact['owner_count']}**" in text
assert f"Business reporting assets: **{impact['business_reporting_asset_count']}**" in text
assert impact["why_it_matters"] in text
for evidence in impact["evidence"]:
    assert f"- {evidence}" in text
for action in impact["actions"]:
    expected_action = (
        f"{action['id']}. **{action['title']}** — Owner: {action['owner']}"
    )
    assert expected_action in text
assert set(document.related_assets or []) == expected_assets
assert prior_count is not None
assert len(related_documents) == int(prior_count.group(1))
PY

jq --null-input \
  --arg run_id "$run_id" \
  --arg document_urn "$document_urn" \
  --argjson affected_assets "$(jq '.impact.affected_asset_count' "$TEMP_DIR/analysis.json")" \
  --argjson actions "$(jq '.impact.actions | length' "$TEMP_DIR/analysis.json")" \
  '{
    status: "passed",
    auth_mode: "chatgpt_oauth",
    run_id: $run_id,
    document_urn: $document_urn,
    datahub_url_verified: true,
    affected_assets: $affected_assets,
    grounded_actions: $actions,
    writeback_reread: true
  }'
