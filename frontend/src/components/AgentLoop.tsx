import { Check, CircleDotDashed, LoaderCircle } from "lucide-react";
import type { AnalysisResponse, RunPhase } from "../types";

interface Props {
  analysis: AnalysisResponse | null;
  phase: RunPhase;
  activeStage: number;
  liveMessage: string;
}

const defaults = [
  { label: "Read context", detail: "Load schema, owners, and governance." },
  { label: "Trace lineage", detail: "Follow the selected column downstream." },
  { label: "Reason", detail: "Assess business and technical risk." },
  { label: "Prepare actions", detail: "Assign grounded remediation steps." },
  { label: "Write back", detail: "Save approved memory to DataHub." },
];

export function AgentLoop({ analysis, phase, activeStage, liveMessage }: Props) {
  return (
    <section className="panel agent-loop" aria-label="Agent loop status">
      <div className="agent-loop-header">
        <h2>Agent loop</h2>
        {analysis && <span>{analysis.run_id}</span>}
      </div>
      <ol className="stage-list">
        {defaults.map((stage, index) => {
          const complete = phase === "written" || index < activeStage || (phase === "ready" && index < 4);
          const active = index === activeStage && ["running", "writing"].includes(phase);
          const waiting = index === 4 && phase === "ready";
          const timing = analysis?.timings[index];
          const detail = phase === "written" && index === 4
            ? "Saved the approved incident-memory document to DataHub."
            : timing?.detail ?? stage.detail;
          return (
            <li key={stage.label} className={complete ? "complete" : active ? "active" : waiting ? "waiting" : "pending"}>
              <span className="stage-icon">
                {complete ? <Check size={18} /> : active ? <LoaderCircle size={18} /> : <CircleDotDashed size={18} />}
              </span>
              <div>
                <strong>{stage.label}</strong>
                <small>
                  {complete ? "Complete" : active ? "Running" : waiting ? "Approval required" : "Pending"}
                  {timing && timing.elapsed_ms > 0 ? ` · ${timing.elapsed_ms}ms` : ""}
                </small>
                <p>{detail}</p>
              </div>
            </li>
          );
        })}
      </ol>
      <div className="live-log" aria-live="polite">
        <span className="live-dot" />
        <strong>Live log</strong>
        <time>{new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</time>
        <p>{liveMessage}</p>
        <span className="log-pulse"><i /><i /><i /></span>
      </div>
    </section>
  );
}
