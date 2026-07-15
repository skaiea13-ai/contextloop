import { BookOpenCheck, Database, ExternalLink, Gauge, Users } from "lucide-react";
import type { AnalysisResponse, RunPhase, WriteBackResponse } from "../types";

interface Props {
  analysis: AnalysisResponse | null;
  phase: RunPhase;
  writeBackResult: WriteBackResponse | null;
  onWriteBack: () => void;
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

export function ImpactPanel({ analysis, phase, writeBackResult, onWriteBack }: Props) {
  return (
    <aside className="panel impact-panel" aria-label="Impact assessment">
      <div className="panel-heading">
        <h2>Impact assessment</h2>
      </div>

      {!analysis ? (
        <div className="impact-empty">
          <div className="impact-empty-icon"><Gauge size={26} /></div>
          <strong>No assessment yet</strong>
          <p>Run the loop to ground a change assessment in live DataHub context.</p>
        </div>
      ) : (
        <>
          <div className="severity-block">
            <p className="severity-title"><span>{analysis.impact.severity}</span> · {analysis.impact.headline}</p>
            <p className="eyeline">Evidence summary</p>
            <div className="metric-line">
              <span><Database size={15} />{analysis.impact.affected_asset_count} assets</span>
              <span><Users size={15} />{analysis.impact.owner_count} owners</span>
              <span><Gauge size={15} />{analysis.impact.business_reporting_asset_count} BI assets</span>
            </div>
          </div>

          <section className="inspector-section">
            <h3>Why it matters</h3>
            <p>{analysis.impact.why_it_matters}</p>
            <ul className="evidence-list">
              {analysis.impact.evidence.map((evidence) => <li key={evidence}>{evidence}</li>)}
            </ul>
          </section>

          <section className="inspector-section actions-section">
            <h3>Recommended actions</h3>
            <ol className="action-list">
              {analysis.impact.actions.map((action) => (
                <li key={action.id}>
                  <span className="action-number">{action.id}</span>
                  <span className="action-title">{action.title}</span>
                  <span className="action-owner" title={action.owner}>
                    <i>{initials(action.owner)}</i>
                    <small>Owner</small>
                    <strong>{action.owner}</strong>
                  </span>
                </li>
              ))}
            </ol>
          </section>

          <div className="writeback-area">
            {writeBackResult ? (
              <a className="writeback-success" href={writeBackResult.datahub_url} target="_blank" rel="noreferrer">
                <BookOpenCheck size={19} />
                Incident memory saved in DataHub
                <ExternalLink size={15} />
              </a>
            ) : (
              <button
                className="writeback-button"
                type="button"
                onClick={onWriteBack}
                disabled={phase !== "ready"}
              >
                <BookOpenCheck size={19} />
                {phase === "writing" ? "Writing to DataHub…" : "Approve & write back to DataHub"}
              </button>
            )}
          </div>
        </>
      )}
    </aside>
  );
}
