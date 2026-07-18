import ReactMarkdown from "react-markdown";
import type { MatchReport, ReproClass, TargetScore } from "../types";

const CLASS_LABEL: Record<ReproClass, string> = {
  exact: "exact",
  "within-tolerance": "within-tol",
  "coarsening-limited": "coarsening",
  "not-reproducible": "not-repro",
};

function fmt(v: Record<string, unknown> | null): string {
  if (!v || v.point == null) return "—";
  const unit = v.unit ? ` ${v.unit}` : "";
  let s = `${v.point}${unit}`;
  if (v.ci_low != null) s += ` (95% CI ${v.ci_low}–${v.ci_high})`;
  return s;
}

function Chip({ c }: { c: ReproClass }) {
  return <span className={`chip ${c}`}>{CLASS_LABEL[c]}</span>;
}

function ScoreRows({ scores }: { scores: TargetScore[] }) {
  return (
    <>
      {scores.map((s) => (
        <tr key={s.target_id}>
          <td>{s.target_id}</td>
          <td><Chip c={s.class} /></td>
          <td>{fmt(s.expected)}</td>
          <td>{fmt(s.observed)}</td>
          <td className={`v-${s.verdict}`}>{s.verdict}</td>
          <td style={{ color: "var(--muted)" }}>{s.reason}</td>
        </tr>
      ))}
    </>
  );
}

export function MatchReportView({ report }: { report: MatchReport }) {
  // Table 1 targets are shown FIRST — a cohort that doesn't match theirs is why an HR won't.
  const t1Ids = new Set(["cohort_n_total", "cohort_n_ge70", "t1_kps_ge90"]);
  const table1 = report.scores.filter((s) => t1Ids.has(s.target_id) || s.target_id.startsWith("t1_"));
  const endpoints = report.scores.filter((s) => !table1.includes(s));

  const v = report.verdict;
  return (
    <div className="panel">
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
        <h2 style={{ margin: 0 }}>Match report</h2>
        <span className={`verdict ${v}`}>{v}</span>
        <span style={{ fontSize: 12, color: "var(--muted)" }}>
          Table 1 {report.table1_reconciled ? "reconciled ✓" : "did not reconcile ✗"}
        </span>
      </div>

      <div className="summary-grid">
        {(Object.keys(report.summary) as ReproClass[]).map((c) => (
          <div className="box" key={c}>
            <b style={{ color: `var(--class-${c === "within-tolerance" ? "within" : c === "coarsening-limited" ? "coarsening" : c === "not-reproducible" ? "notrepro" : "exact"})` }}>
              {report.summary[c].matched ?? 0}/{report.summary[c].total}
            </b>
            {c}
          </div>
        ))}
      </div>

      <div className="section-label">Table 1 — cohort (checked first)</div>
      <table className="scores">
        <thead>
          <tr><th>Target</th><th>Class</th><th>Expected</th><th>Observed</th><th>Verdict</th><th>Why</th></tr>
        </thead>
        <tbody><ScoreRows scores={table1} /></tbody>
      </table>

      <div className="section-label">Endpoints</div>
      <table className="scores">
        <thead>
          <tr><th>Target</th><th>Class</th><th>Expected</th><th>Observed</th><th>Verdict</th><th>Why</th></tr>
        </thead>
        <tbody><ScoreRows scores={endpoints} /></tbody>
      </table>

      {report.body && (
        <div style={{ marginTop: 14, fontSize: 13, color: "var(--muted)" }}>
          <ReactMarkdown>{report.body}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}
