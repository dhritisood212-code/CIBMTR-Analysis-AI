import { useState } from "react";
import type { RunState } from "../types";

/** The R script viewer + downloadable bundle list. The script is read-only on purpose — the
 *  point is that it's inspectable and rerunnable, the acceptance bar being "would a
 *  biostatistician merge this PR?". */
export function ArtifactBundle({
  run,
  script,
  onDownload,
}: {
  run: RunState;
  script: string;
  onDownload: (name: string) => void;
}) {
  const [tab, setTab] = useState<"script" | "bundle">("script");
  return (
    <div className="panel">
      <div className="tabs">
        <button className={tab === "script" ? "active" : ""} onClick={() => setTab("script")}>
          reproduce_{run.study_id.replace("-SYNTHETIC", "")}.R
        </button>
        <button className={tab === "bundle" ? "active" : ""} onClick={() => setTab("bundle")}>
          Bundle ({run.artifacts.length})
        </button>
      </div>

      {tab === "script" ? (
        <pre className="code">{script}</pre>
      ) : (
        <div>
          <p style={{ fontSize: 13, color: "var(--muted)" }}>
            Deterministic, git-committed per run. Rerunning the script regenerates every table.
          </p>
          <ul style={{ fontSize: 13, listStyle: "none", padding: 0 }}>
            {[...run.artifacts, "results/*.csv", "renv.lock", "sessionInfo.txt"].map((a) => (
              <li key={a} style={{ padding: "4px 0", display: "flex", gap: 10 }}>
                <span style={{ color: "var(--muted)", width: 220 }}>{a}</span>
                <a href="#" onClick={(e) => { e.preventDefault(); onDownload(a); }}>download</a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
