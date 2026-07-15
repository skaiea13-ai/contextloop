import { Box, CheckCircle2, ShieldCheck } from "lucide-react";
import type { BootstrapResponse } from "../types";

interface Props {
  bootstrap: BootstrapResponse | null;
}

export function FooterStatus({ bootstrap }: Props) {
  const modelStatus = bootstrap?.execution_mode === "deterministic_fixture"
    ? "Fixture · no model call"
    : `Codex Auth · ${bootstrap?.model ?? "checking…"}`;
  return (
    <footer className="status-footer">
      <span><ShieldCheck size={17} />{modelStatus}</span>
      <span><Box size={17} />DataHub v{bootstrap?.datahub_version ?? "…"}</span>
      <span className="no-key"><CheckCircle2 size={18} />No API key required</span>
    </footer>
  );
}
