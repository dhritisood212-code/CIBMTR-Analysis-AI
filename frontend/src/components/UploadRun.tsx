import { useState } from "react";
import type { StudyCatalogEntry } from "../types";

export interface LaunchBody {
  study_id: string;
  tc_confirmed: boolean;
  primary_endpoint?: string;
  new_study_plan?: string;
  dataset?: File;
  dictionary?: File;
}

/** The "Upload & Run" tab: attach a dataset and start a run in one place, either against a
 *  catalog study or as a standalone "new-study" analysis (bring your own plan). */
export function UploadRun({
  studies,
  onLaunch,
}: {
  studies: StudyCatalogEntry[];
  onLaunch: (body: LaunchBody) => void;
}) {
  const [mode, setMode] = useState<"catalog" | "custom">("catalog");
  const [studyId, setStudyId] = useState(studies[0]?.study_id ?? "");
  const [plan, setPlan] = useState("");
  const [endpoint, setEndpoint] = useState("OS");
  const [tc, setTc] = useState(false);
  const [dataset, setDataset] = useState<File | undefined>();
  const [dictionary, setDictionary] = useState<File | undefined>();

  const selected = studies.find((s) => s.study_id === studyId);
  const canRun =
    tc && !!dataset && (mode === "catalog" ? !!studyId : plan.trim().length > 0);

  function launch() {
    onLaunch({
      study_id: mode === "catalog" ? studyId : "custom-analysis",
      tc_confirmed: tc,
      primary_endpoint: mode === "catalog" ? endpoint : undefined,
      new_study_plan: mode === "custom" ? plan.trim() : undefined,
      dataset,
      dictionary,
    });
  }

  return (
    <div className="panel">
      <h2>Upload &amp; run</h2>

      <div className="tabs" style={{ marginBottom: 14 }}>
        <button className={mode === "catalog" ? "active" : ""} onClick={() => setMode("catalog")}>
          Reproduce a catalog study
        </button>
        <button className={mode === "custom" ? "active" : ""} onClick={() => setMode("custom")}>
          New analysis (your own plan)
        </button>
      </div>

      {mode === "catalog" ? (
        <>
          <label style={{ fontSize: 13, display: "block", marginBottom: 10 }}>
            <div className="meta" style={{ marginBottom: 4 }}>Study</div>
            <select value={studyId} onChange={(e) => setStudyId(e.target.value)} style={{ minWidth: 320 }}>
              {studies.map((s) => (
                <option key={s.study_id} value={s.study_id}>
                  {s.study_id} — {s.title.slice(0, 60)}{s.title.length > 60 ? "…" : ""}
                </option>
              ))}
            </select>
          </label>
          {selected && (
            <p style={{ fontSize: 12, color: "var(--muted)", margin: "0 0 10px" }}>
              Download this study's data from{" "}
              <a href={selected.dataset_download_url} target="_blank" rel="noreferrer">CIBMTR (dataset)</a>{" "}
              and its{" "}
              <a href={selected.data_dictionary_url} target="_blank" rel="noreferrer">data dictionary</a>,
              under CIBMTR's{" "}
              <a href={selected.terms_url} target="_blank" rel="noreferrer">Terms &amp; Conditions</a>.
            </p>
          )}
          <label style={{ fontSize: 13 }}>
            Start with endpoint:{" "}
            <select value={endpoint} onChange={(e) => setEndpoint(e.target.value)}>
              <option>OS</option><option>PFS</option><option>NRM</option><option>relapse/progression</option>
            </select>
          </label>
        </>
      ) : (
        <>
          <label style={{ fontSize: 13, display: "block" }}>
            <div className="meta" style={{ marginBottom: 4 }}>Your analysis plan</div>
            <textarea
              value={plan}
              onChange={(e) => setPlan(e.target.value)}
              placeholder="Describe the cohort, endpoints, exposure, and models you want drafted — e.g. 'OS and NRM by donor type, adjusted for age and HCT-CI, in adult AML transplants 2015–2020.'"
              rows={5}
              style={{ width: "100%", background: "var(--panel-2)", color: "var(--text)",
                       border: "1px solid var(--border)", borderRadius: 7, padding: 10, fontSize: 13 }}
            />
          </label>
          <p style={{ fontSize: 12, color: "var(--muted)", margin: "6px 0 0" }}>
            New-study mode drafts an analysis for expert review — there's no published target to
            score against. This mode is experimental.
          </p>
        </>
      )}

      <div style={{ margin: "14px 0", display: "grid", gap: 10 }}>
        <label style={{ fontSize: 13 }}>
          <div className="meta" style={{ marginBottom: 4 }}>Dataset (.zip) — required</div>
          <input type="file" accept=".zip,.csv,.tsv,.txt"
                 onChange={(e) => setDataset(e.target.files?.[0])} style={{ fontSize: 13 }} />
        </label>
        <label style={{ fontSize: 13 }}>
          <div className="meta" style={{ marginBottom: 4 }}>Data dictionary (.xlsx / .rtf) — optional</div>
          <input type="file" accept=".xlsx,.xlsm,.rtf,.csv,.txt"
                 onChange={(e) => setDictionary(e.target.files?.[0])} style={{ fontSize: 13 }} />
        </label>
        <div className="meta">Session-scoped &amp; ephemeral · never persisted server-side.</div>
      </div>

      <label className="check">
        <input type="checkbox" checked={tc} onChange={(e) => setTc(e.target.checked)} />
        <span>
          I obtained this data lawfully (for CIBMTR datasets, downloaded under CIBMTR's Terms &amp;
          Conditions). I understand this is a research/educational tool, outputs are drafts for
          expert review, and <b>CIBMTR did not review or endorse</b> any analysis produced here.
        </span>
      </label>

      <button disabled={!canRun} onClick={launch} style={{ marginTop: 4 }}>Run</button>
      {!dataset && tc && (
        <div className="meta" style={{ marginTop: 8 }}>Attach the dataset file to enable the run.</div>
      )}
    </div>
  );
}
