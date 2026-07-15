import { AlertTriangle, Check, ChevronRight, Play, Search } from "lucide-react";
import type { ChangeType, RecentRun } from "../types";

interface Props {
  assetName: string;
  column: string;
  environment: string;
  changeType: ChangeType;
  recentRuns: RecentRun[];
  busy: boolean;
  onColumnChange: (value: string) => void;
  onEnvironmentChange: (value: string) => void;
  onChangeType: (value: ChangeType) => void;
  onRun: () => void;
}

const changeTypes: { value: ChangeType; label: string }[] = [
  { value: "add_column", label: "Add column" },
  { value: "drop_column", label: "Drop column" },
  { value: "modify_column", label: "Modify column" },
];

export function ChangeTrigger({
  assetName,
  column,
  environment,
  changeType,
  recentRuns,
  busy,
  onColumnChange,
  onEnvironmentChange,
  onChangeType,
  onRun,
}: Props) {
  return (
    <aside className="panel left-rail" aria-label="Change trigger">
      <div className="panel-heading">
        <h2>Change trigger</h2>
      </div>

      <div className="field-group">
        <label htmlFor="asset">Asset</label>
        <div className="input-shell read-only">
          <Search size={15} aria-hidden="true" />
          <input id="asset" value={assetName} readOnly />
        </div>
      </div>

      <fieldset className="field-group">
        <legend>Change type</legend>
        <div className="segmented-control">
          {changeTypes.map((type) => (
            <button
              key={type.value}
              type="button"
              className={type.value === changeType ? "selected" : ""}
              onClick={() => onChangeType(type.value)}
              disabled={busy}
            >
              {type.label}
            </button>
          ))}
        </div>
      </fieldset>

      <div className="field-group">
        <label htmlFor="column">Column</label>
        <input
          id="column"
          className="text-input"
          value={column}
          onChange={(event) => onColumnChange(event.target.value)}
          disabled={busy}
          spellCheck={false}
        />
      </div>

      <div className="field-group">
        <label htmlFor="environment">Environment</label>
        <select
          id="environment"
          className="text-input"
          value={environment}
          onChange={(event) => onEnvironmentChange(event.target.value)}
          disabled={busy}
        >
          <option value="PROD">PROD</option>
          <option value="STG">STG</option>
          <option value="DEV">DEV</option>
        </select>
      </div>

      <button className="run-button" type="button" onClick={onRun} disabled={busy || !column}>
        <Play size={18} fill="currentColor" aria-hidden="true" />
        {busy ? "Tracing impact…" : "Run impact loop"}
      </button>

      <div className="recent-runs">
        <h3>Recent runs</h3>
        {recentRuns.length === 0 ? (
          <p className="empty-copy">Completed analyses will appear here.</p>
        ) : (
          <ul>
            {recentRuns.map((run, index) => (
              <li key={run.id} className={index === 0 ? "active" : ""}>
                <span className={`run-status ${run.severity === "P1" ? "risk" : "ok"}`}>
                  {["P0", "P1"].includes(run.severity) ? (
                    <AlertTriangle size={16} aria-hidden="true" />
                  ) : (
                    <Check size={16} aria-hidden="true" />
                  )}
                </span>
                <span className="run-summary">
                  <strong>{run.id}</strong>
                  <span>{run.change}</span>
                  <time>{run.createdAt}</time>
                </span>
                <ChevronRight size={16} aria-hidden="true" />
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
