import { ExternalLink, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { AgentLoop } from "./components/AgentLoop";
import { Brand } from "./components/Brand";
import { ChangeTrigger } from "./components/ChangeTrigger";
import { FooterStatus } from "./components/FooterStatus";
import { ImpactPanel } from "./components/ImpactPanel";
import { LineageCanvas } from "./components/LineageCanvas";
import { analyzeChange, loadBootstrap, writeBack } from "./lib/api";
import type {
  AnalysisResponse,
  AnalyzeRequest,
  BootstrapResponse,
  ChangeType,
  GraphNode,
  RecentRun,
  RunPhase,
  WriteBackResponse,
} from "./types";

function formatRunTime(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function App() {
  const [bootstrap, setBootstrap] = useState<BootstrapResponse | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [writeBackResult, setWriteBackResult] = useState<WriteBackResponse | null>(null);
  const [phase, setPhase] = useState<RunPhase>("idle");
  const [activeStage, setActiveStage] = useState(0);
  const [column, setColumn] = useState("discount_amount");
  const [changeType, setChangeType] = useState<ChangeType>("drop_column");
  const [environment, setEnvironment] = useState("PROD");
  const [recentRuns, setRecentRuns] = useState<RecentRun[]>([]);
  const [error, setError] = useState<string | null>(null);
  const stageTimer = useRef<number | null>(null);

  useEffect(() => {
    loadBootstrap()
      .then((payload) => {
        setBootstrap(payload);
        setColumn(payload.default_column);
      })
      .catch((reason: Error) => setError(reason.message));
    return () => {
      if (stageTimer.current) window.clearInterval(stageTimer.current);
    };
  }, []);

  const request = useMemo<AnalyzeRequest | null>(() => {
    if (!bootstrap) return null;
    return {
      asset_urn: bootstrap.default_asset_urn,
      asset_name: bootstrap.default_asset_name,
      column,
      change_type: changeType,
      environment,
    };
  }, [bootstrap, column, changeType, environment]);

  const initialNodes = useMemo<GraphNode[]>(() => {
    if (!bootstrap || analysis) return analysis?.nodes ?? [];
    return [
      {
        id: "source",
        urn: bootstrap.default_asset_urn,
        name: "order_details",
        platform: "dbt",
        entity_type: "dataset",
        column,
        selected: true,
        owners: [],
      },
    ];
  }, [bootstrap, analysis, column]);

  function startStageAnimation() {
    setActiveStage(0);
    if (stageTimer.current) window.clearInterval(stageTimer.current);
    stageTimer.current = window.setInterval(() => {
      setActiveStage((stage) => Math.min(3, stage + 1));
    }, 900);
  }

  async function runAnalysis() {
    if (!request) return;
    setError(null);
    setWriteBackResult(null);
    setPhase("running");
    startStageAnimation();
    try {
      const result = await analyzeChange(request);
      if (stageTimer.current) window.clearInterval(stageTimer.current);
      setAnalysis(result);
      setActiveStage(4);
      setPhase("ready");
      setRecentRuns((runs) => [
        {
          id: result.run_id,
          change: `${changeType.replaceAll("_", " ")} · ${column}`,
          createdAt: formatRunTime(result.created_at),
          severity: result.impact.severity,
        },
        ...runs,
      ].slice(0, 4));
    } catch (reason) {
      if (stageTimer.current) window.clearInterval(stageTimer.current);
      setPhase("idle");
      setActiveStage(0);
      setError(reason instanceof Error ? reason.message : "Analysis failed");
    }
  }

  async function approveWriteBack() {
    if (!analysis || !request) return;
    setError(null);
    setPhase("writing");
    setActiveStage(4);
    try {
      const result = await writeBack(analysis);
      setWriteBackResult(result);
      setPhase("written");
      setActiveStage(5);
    } catch (reason) {
      setPhase("ready");
      setError(reason instanceof Error ? reason.message : "Write-back failed");
    }
  }

  const liveMessage =
    phase === "running"
      ? [
          "Reading live schema and ownership context from DataHub…",
          `Tracing downstream lineage for ${column}…`,
          bootstrap?.execution_mode === "deterministic_fixture"
            ? "The deterministic no-model fixture is preparing the impact assessment…"
            : "Codex OAuth is evaluating the grounded impact graph…",
          "Preparing actions with owners from DataHub…",
        ][Math.min(activeStage, 3)]
      : phase === "ready"
        ? "Impact plan ready. Explicit approval is required before DataHub is changed."
        : phase === "writing"
          ? "Saving a related incident-memory document through Agent Context Kit…"
          : phase === "written"
            ? `Write-back complete: ${writeBackResult?.document_urn ?? "DataHub document saved"}`
            : "Waiting for a schema change trigger.";

  return (
    <div className="app-shell">
      <header className="topbar">
        <Brand />
        <div className="breadcrumb">
          <span>Incidents</span><i>/</i><strong>{analysis ? `Schema change #${analysis.run_id}` : "New schema change"}</strong>
        </div>
        <div className="topbar-actions">
          <span className={bootstrap?.datahub.ok ? "connection good" : "connection"}>
            DataHub OSS <i /> {bootstrap?.datahub.ok ? "Connected" : "Checking"}
          </span>
          <a href="http://localhost:9002" target="_blank" rel="noreferrer">
            Open in DataHub <ExternalLink size={14} />
          </a>
        </div>
      </header>

      {error && (
        <div className="error-banner" role="alert">
          <span>{error}</span>
          <button type="button" onClick={() => setError(null)}><RefreshCw size={15} />Dismiss</button>
        </div>
      )}

      <main className="workspace">
        <ChangeTrigger
          assetName={bootstrap?.default_asset_name ?? "analytics.order_details"}
          column={column}
          environment={environment}
          changeType={changeType}
          recentRuns={recentRuns}
          busy={phase === "running" || phase === "writing"}
          onColumnChange={setColumn}
          onEnvironmentChange={setEnvironment}
          onChangeType={setChangeType}
          onRun={runAnalysis}
        />
        <LineageCanvas nodes={initialNodes} column={column} loading={phase === "running"} />
        <ImpactPanel
          analysis={analysis}
          phase={phase}
          writeBackResult={writeBackResult}
          onWriteBack={approveWriteBack}
        />
        <AgentLoop
          analysis={analysis}
          phase={phase}
          activeStage={activeStage}
          liveMessage={liveMessage}
        />
      </main>

      <FooterStatus bootstrap={bootstrap} />
    </div>
  );
}
