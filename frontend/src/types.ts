export type ChangeType = "drop_column" | "modify_column" | "add_column";

export interface ServiceStatus {
  ok: boolean;
  label: string;
  detail: string;
}

export interface BootstrapResponse {
  datahub: ServiceStatus;
  codex: ServiceStatus;
  default_asset_urn: string;
  default_asset_name: string;
  default_column: string;
  datahub_version: string;
  model: string;
  execution_mode: "chatgpt_oauth" | "deterministic_fixture";
}

export interface Owner {
  name: string;
  role: string;
}

export interface GraphNode {
  id: string;
  urn: string;
  name: string;
  platform: string;
  entity_type: string;
  column: string | null;
  selected: boolean;
  owners: Owner[];
}

export interface GraphEdge {
  source: string;
  target: string;
  kind: "selected" | "downstream";
}

export interface ImpactAction {
  id: number;
  title: string;
  owner: string;
  priority: "now" | "next" | "monitor";
}

export interface ImpactAssessment {
  severity: "P0" | "P1" | "P2" | "P3";
  headline: string;
  summary: string;
  why_it_matters: string;
  affected_asset_count: number;
  owner_count: number;
  business_reporting_asset_count: number;
  evidence: string[];
  actions: ImpactAction[];
}

export interface AgentTiming {
  stage: "read" | "trace" | "reason" | "prepare" | "write";
  label: string;
  detail: string;
  elapsed_ms: number;
  status: "complete" | "waiting";
}

export interface AnalysisResponse {
  run_id: string;
  created_at: string;
  source_asset: GraphNode;
  nodes: GraphNode[];
  edges: GraphEdge[];
  impact: ImpactAssessment;
  timings: AgentTiming[];
  model: string;
  auth_mode: "chatgpt_oauth" | "fixture";
}

export interface AnalyzeRequest {
  asset_urn: string;
  asset_name: string;
  column: string;
  change_type: ChangeType;
  environment: string;
}

export interface WriteBackResponse {
  document_urn: string;
  title: string;
  datahub_url: string;
  saved_at: string;
}

export type RunPhase = "idle" | "running" | "ready" | "writing" | "written";

export interface RecentRun {
  id: string;
  change: string;
  createdAt: string;
  severity: string;
}
