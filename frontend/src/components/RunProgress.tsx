import type { RunState } from "../types";

const STAGE_LABEL: Record<string, string> = {
  interpret: "Interpret paper → spec + targets (classes assigned)",
  build_cohort: "Build cohort (derive from raw + self-check)",
  assemble_cohort: "Assemble cohort → Table 1 + attrition",
  analyze: "Analyze → reproduce_<study>.R + results",
  compare: "Compare → match report",
  diagnose: "Diagnose mismatch",
  done: "Done",
};

/** Stage timeline from RunState.events. Shows the panel advancing through the six agents. */
export function RunProgress({ run }: { run: RunState }) {
  const seen = new Map<string, string>();
  for (const e of run.events) seen.set(e.stage, e.status);

  return (
    <div className="panel">
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <h2 style={{ margin: 0 }}>Run {run.run_id}</h2>
        <span style={{ fontSize: 12, color: "var(--muted)" }}>status: {run.status}</span>
      </div>
      <ul className="timeline" style={{ marginTop: 10 }}>
        {Object.keys(STAGE_LABEL).map((stage) => {
          const st = seen.get(stage) ?? "pending";
          return (
            <li key={stage}>
              <span className={`dot ${st}`} />
              <span style={{ color: st === "pending" ? "var(--muted)" : "var(--text)" }}>
                {STAGE_LABEL[stage]}
              </span>
            </li>
          );
        })}
      </ul>
      {run.error && (
        <div style={{ color: "var(--verdict-fail)", fontSize: 13, marginTop: 8 }}>{run.error}</div>
      )}
    </div>
  );
}
