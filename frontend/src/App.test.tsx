import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import App from "./App";
import type { AnalysisResponse, BootstrapResponse, WriteBackResponse } from "./types";

const bootstrapResponse: BootstrapResponse = {
  datahub: { ok: true, label: "DataHub OSS", detail: "connected" },
  codex: { ok: true, label: "Codex Auth", detail: "Logged in using ChatGPT" },
  default_asset_urn: "urn:li:dataset:test-source",
  default_asset_name: "analytics.order_details",
  default_column: "discount_amount",
  datahub_version: "1.6.0",
  model: "gpt-5.6-sol",
  execution_mode: "chatgpt_oauth",
};

const analysisResponse: AnalysisResponse = {
  run_id: "CL-TEST",
  created_at: "2026-07-15T09:30:00Z",
  source_asset: {
    id: "source",
    urn: "urn:li:dataset:test-source",
    name: "analytics.order_details",
    platform: "dbt",
    entity_type: "dataset",
    column: "discount_amount",
    selected: true,
    owners: [{ name: "Data Platform Team", role: "Technical Owner" }],
  },
  nodes: [
    {
      id: "source",
      urn: "urn:li:dataset:test-source",
      name: "analytics.order_details",
      platform: "dbt",
      entity_type: "dataset",
      column: "discount_amount",
      selected: true,
      owners: [{ name: "Data Platform Team", role: "Technical Owner" }],
    },
    {
      id: "revenue-dashboard",
      urn: "urn:li:dashboard:revenue",
      name: "Revenue dashboard",
      platform: "looker",
      entity_type: "dashboard",
      column: "discount_amount",
      selected: false,
      owners: [{ name: "Ian Chen", role: "Business Owner" }],
    },
  ],
  edges: [{ source: "source", target: "revenue-dashboard", kind: "downstream" }],
  impact: {
    severity: "P1",
    headline: "Block PROD drop: revenue reporting is at risk",
    summary: "The proposed drop affects a downstream business dashboard.",
    why_it_matters: "Revenue reporting depends on the selected column.",
    affected_asset_count: 1,
    owner_count: 2,
    business_reporting_asset_count: 1,
    evidence: [
      "DataHub schema confirms discount_amount on analytics.order_details.",
      "Column lineage reaches the Revenue dashboard.",
    ],
    actions: [
      { id: 1, title: "Block the PROD column drop", owner: "Data Platform Team", priority: "now" },
      { id: 2, title: "Update the revenue dashboard", owner: "Ian Chen", priority: "now" },
      { id: 3, title: "Confirm a safe rollout plan", owner: "Data Platform Team", priority: "next" },
    ],
  },
  timings: [
    { stage: "read", label: "Read context", detail: "Loaded DataHub context.", elapsed_ms: 20, status: "complete" },
    { stage: "trace", label: "Trace lineage", detail: "Found one dependency.", elapsed_ms: 30, status: "complete" },
    { stage: "reason", label: "Reason", detail: "Assessed the grounded risk.", elapsed_ms: 40, status: "complete" },
    { stage: "prepare", label: "Prepare actions", detail: "Prepared owner actions.", elapsed_ms: 10, status: "complete" },
    { stage: "write", label: "Write back", detail: "Awaiting explicit approval.", elapsed_ms: 0, status: "waiting" },
  ],
  model: "gpt-5.6-sol",
  auth_mode: "chatgpt_oauth",
};

const writeBackResponse: WriteBackResponse = {
  document_urn: "urn:li:document:contextloop-test",
  title: "ContextLoop CL-TEST incident memory",
  datahub_url: "http://localhost:9002/document/urn:li:document:contextloop-test",
  saved_at: "2026-07-15T09:31:00Z",
};

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

interface ApiMockOptions {
  bootstrap?: BootstrapResponse;
  onWriteBack?: (attempt: number) => Response | Promise<Response>;
}

function installApiMock(options: ApiMockOptions = {}) {
  let writeBackAttempt = 0;
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.pathname : input.url;
    if (url === "/api/bootstrap") return jsonResponse(options.bootstrap ?? bootstrapResponse);
    if (url === "/api/analyze") return jsonResponse(analysisResponse);
    if (url === "/api/write-back") {
      writeBackAttempt += 1;
      return options.onWriteBack?.(writeBackAttempt) ?? jsonResponse(writeBackResponse);
    }
    throw new Error(`Unexpected request: ${url}`);
  });
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("ContextLoop impact flow", () => {
  test("runs a grounded analysis and writes back only after explicit approval", async () => {
    const fetchMock = installApiMock();
    render(<App />);

    expect(screen.getByText("No API key required")).toBeTruthy();
    expect(await screen.findByDisplayValue("analytics.order_details")).toBeTruthy();
    expect(screen.getByText("Codex Auth · gpt-5.6-sol")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Run impact loop" }));

    expect(await screen.findByText(analysisResponse.impact.headline, { exact: false })).toBeTruthy();
    expect(screen.getByText("Revenue reporting depends on the selected column.")).toBeTruthy();
    expect(screen.getByText("Column lineage reaches the Revenue dashboard.")).toBeTruthy();
    expect(screen.getByText("Impact plan ready. Explicit approval is required before DataHub is changed.")).toBeTruthy();

    expect(fetchMock.mock.calls[1]?.[0]).toBe("/api/analyze");
    expect(fetchMock.mock.calls[1]?.[1]?.method).toBe("POST");
    expect(JSON.parse(String(fetchMock.mock.calls[1]?.[1]?.body))).toEqual({
      asset_urn: "urn:li:dataset:test-source",
      asset_name: "analytics.order_details",
      column: "discount_amount",
      change_type: "drop_column",
      environment: "PROD",
    });
    expect(fetchMock.mock.calls.some(([input]) => input === "/api/write-back")).toBe(false);

    const approvalButton = screen.getByRole("button", { name: "Approve & write back to DataHub" });
    expect((approvalButton as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(approvalButton);

    const savedLink = await screen.findByRole("link", { name: /Incident memory saved in DataHub/ });
    expect(savedLink.getAttribute("href")).toBe(writeBackResponse.datahub_url);
    expect(screen.getByText(`Write-back complete: ${writeBackResponse.document_urn}`)).toBeTruthy();

    expect(fetchMock.mock.calls[2]?.[0]).toBe("/api/write-back");
    expect(fetchMock.mock.calls[2]?.[1]?.method).toBe("POST");
    expect(JSON.parse(String(fetchMock.mock.calls[2]?.[1]?.body))).toEqual({
      run_id: analysisResponse.run_id,
      approved: true,
    });
  });

  test("recovers from a write-back error and lets the user retry the same approved analysis", async () => {
    const fetchMock = installApiMock({
      onWriteBack: (attempt) =>
        attempt === 1
          ? jsonResponse({ detail: "DataHub write-back temporarily unavailable" }, 503)
          : jsonResponse(writeBackResponse),
    });
    render(<App />);

    await screen.findByDisplayValue("analytics.order_details");
    fireEvent.click(screen.getByRole("button", { name: "Run impact loop" }));
    await screen.findByText(analysisResponse.impact.headline, { exact: false });

    fireEvent.click(screen.getByRole("button", { name: "Approve & write back to DataHub" }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("DataHub write-back temporarily unavailable");
    expect(screen.getByText("Revenue reporting depends on the selected column.")).toBeTruthy();

    const retryButton = screen.getByRole("button", { name: "Approve & write back to DataHub" });
    await waitFor(() => expect((retryButton as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(retryButton);

    expect(await screen.findByRole("link", { name: /Incident memory saved in DataHub/ })).toBeTruthy();
    expect(screen.queryByRole("alert")).toBeNull();
    expect(fetchMock.mock.calls.filter(([input]) => input === "/api/write-back")).toHaveLength(2);
  });

  test("visibly labels deterministic fixture mode as making no model call", async () => {
    installApiMock({
      bootstrap: {
        ...bootstrapResponse,
        codex: {
          ok: true,
          label: "Codex Auth",
          detail: "Deterministic fixture enabled; no model call",
        },
        execution_mode: "deterministic_fixture",
      },
    });
    render(<App />);

    expect(await screen.findByText("Fixture · no model call")).toBeTruthy();
    expect(screen.getByText("No API key required")).toBeTruthy();
    expect(screen.queryByText(/Codex Auth ·/)).toBeNull();
  });
});
