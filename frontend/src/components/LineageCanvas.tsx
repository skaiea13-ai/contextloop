import { Expand, Info, Minus, Plus } from "lucide-react";
import { useMemo, useState } from "react";
import type { GraphNode } from "../types";

interface Props {
  nodes: GraphNode[];
  column: string;
  loading: boolean;
}

interface PositionedNode extends GraphNode {
  x: number;
  y: number;
}

const platformColor: Record<string, string> = {
  dbt: "#ff735f",
  snowflake: "#35c4ef",
  looker: "#a58cff",
  powerbi: "#f6c744",
  tableau: "#59a5ff",
};

function shortName(name: string): string {
  return name.length > 24 ? `${name.slice(0, 22)}…` : name;
}

function positions(nodes: GraphNode[]): PositionedNode[] {
  if (nodes.length === 0) return [];
  const source = { ...nodes[0], x: 42, y: 205 };
  const downstream = nodes.slice(1, 8);
  const bridge = downstream.filter((node) => ["snowflake", "looker"].includes(node.platform)).slice(0, 2);
  const bridgeIds = new Set(bridge.map((node) => node.id));
  const leaves = downstream.filter((node) => !bridgeIds.has(node.id));
  const bridgePositions = bridge.map((node, index) => ({
    ...node,
    x: 338,
    y: bridge.length === 1 ? 205 : 105 + index * 210,
  }));
  const leafPositions = leaves.slice(0, 4).map((node, index) => ({
    ...node,
    x: 645,
    y: 22 + index * 116,
  }));
  return [source, ...bridgePositions, ...leafPositions];
}

export function LineageCanvas({ nodes, column, loading }: Props) {
  const [zoom, setZoom] = useState(1);
  const positioned = useMemo(() => positions(nodes), [nodes]);
  const source = positioned[0];

  return (
    <section className="panel lineage-panel" aria-label="Column impact projection">
      <div className="panel-heading lineage-heading">
        <div>
          <h2>Column impact projection</h2>
          <Info size={15} aria-label="Bounded downstream lineage results from DataHub" />
        </div>
        <div className="canvas-controls" aria-label="Lineage zoom controls">
          <button type="button" onClick={() => setZoom((value) => Math.max(0.8, value - 0.1))}>
            <Minus size={15} aria-label="Zoom out" />
          </button>
          <span>{Math.round(zoom * 100)}%</span>
          <button type="button" onClick={() => setZoom((value) => Math.min(1.2, value + 0.1))}>
            <Plus size={15} aria-label="Zoom in" />
          </button>
          <button type="button" className="reset-control" onClick={() => setZoom(1)}>
            Reset
          </button>
          <button type="button" onClick={() => setZoom(1.1)}>
            <Expand size={15} aria-label="Fit lineage" />
          </button>
        </div>
      </div>

      <div className={`lineage-stage ${loading ? "is-loading" : ""}`}>
        {positioned.length === 0 ? (
          <div className="lineage-empty">
            <span className="empty-orbit" />
            <strong>Ready to query live lineage</strong>
            <p>Run the impact loop to project DataHub’s bounded lineage results.</p>
          </div>
        ) : (
          <svg
            viewBox="0 0 900 500"
            role="img"
            aria-label={`Bounded downstream impact projection for ${column}`}
            style={{ transform: `scale(${zoom})` }}
          >
            <defs>
              <marker id="arrow-risk" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                <path d="M0,0 L8,4 L0,8 z" fill="#ff5b57" />
              </marker>
            </defs>
            {source &&
              positioned.slice(1).map((node, index) => {
                const startX = source.x + 202;
                const startY = source.y + 52;
                const endX = node.x;
                const endY = node.y + 52;
                const bend = 64 + index * 6;
                return (
                  <path
                    key={`edge-${node.id}`}
                    className="lineage-edge"
                    d={`M ${startX} ${startY} C ${startX + bend} ${startY}, ${endX - bend} ${endY}, ${endX} ${endY}`}
                    markerEnd="url(#arrow-risk)"
                  />
                );
              })}
            {positioned.map((node) => (
              <g key={node.id} transform={`translate(${node.x} ${node.y})`} className="graph-node">
                <rect className={node.selected ? "node-surface selected" : "node-surface"} width="202" height="104" rx="10" />
                <circle cx="22" cy="25" r="10" fill={platformColor[node.platform] ?? "#5f89ff"} opacity="0.18" />
                <text x="22" y="29" textAnchor="middle" className="platform-glyph" fill={platformColor[node.platform] ?? "#5f89ff"}>
                  {node.platform.slice(0, 1).toUpperCase()}
                </text>
                <text x="40" y="27" className="node-name">{shortName(node.name)}</text>
                <text x="40" y="46" className="node-type">{node.platform} · {node.entity_type}</text>
                <line x1="14" y1="62" x2="188" y2="62" className="node-divider" />
                <text x="16" y="84" className="node-column">{column}</text>
                {node.selected && <text x="156" y="84" className="selected-label">SOURCE</text>}
              </g>
            ))}
          </svg>
        )}

        <div className="lineage-legend" aria-label="Lineage legend">
          <span><i className="legend-risk" />Selected column impact</span>
          <span><i className="legend-node" />DataHub asset</span>
        </div>
        {nodes.length > positioned.length && (
          <div className="overflow-count">+{nodes.length - positioned.length} more impacted assets</div>
        )}
      </div>
    </section>
  );
}
