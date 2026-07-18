import { useState } from "react";
import type { StudyCatalogEntry } from "../types";

export interface StartOpts {
  tc: boolean;
  endpoint?: string;
  dataset?: File;
  dictionary?: File;
}

/** Compliance gate: the user confirms they downloaded the dataset from CIBMTR and accepted its
 *  Terms & Conditions, then attaches the dataset + dictionary for this session (ephemeral,
 *  deleted when the run ends). The app never fetches or stores the data itself. */
export function ComplianceGate({
  study,
  onStart,
  onBack,
}: {
  study: StudyCatalogEntry;
  onStart: (opts: StartOpts) => void;
  onBack: () => void;
}) {
  const [tc, setTc] = useState(false);
  const [endpoint, setEndpoint] = useState("OS");
  const [dataset, setDataset] = useState<File | undefined>();
  const [dictionary, setDictionary] = useState<File | undefined>();

  const canRun = tc && !!dataset; // need the dataset at minimum

  return (
    <div className="panel">
      <h2>Session setup — {study.study_id}</h2>
      <p style={{ fontSize: 13, color: "var(--muted)" }}>
        This app stores only study metadata and links. Download the dataset yourself from{" "}
        <a href={study.dataset_download_url} target="_blank" rel="noreferrer">CIBMTR</a> and its{" "}
        <a href={study.data_dictionary_url} target="_blank" rel="noreferrer">data dictionary</a>,
        accepting CIBMTR's{" "}
        <a href={study.terms_url} target="_blank" rel="noreferrer">Terms &amp; Conditions</a>.
        Your uploads are session-scoped and deleted when the run ends.
      </p>

      <div style={{ margin: "12px 0", display: "grid", gap: 10 }}>
        <label style={{ fontSize: 13 }}>
          <div className="meta" style={{ marginBottom: 4 }}>Dataset (.zip) — required</div>
          <input
            type="file"
            accept=".zip,.csv,.tsv,.txt"
            onChange={(e) => setDataset(e.target.files?.[0])}
            style={{ fontSize: 13 }}
          />
        </label>
        <label style={{ fontSize: 13 }}>
          <div className="meta" style={{ marginBottom: 4 }}>Data dictionary (.xlsx / .rtf) — optional but recommended</div>
          <input
            type="file"
            accept=".xlsx,.xlsm,.rtf,.csv,.txt"
            onChange={(e) => setDictionary(e.target.files?.[0])}
            style={{ fontSize: 13 }}
          />
        </label>
        <div className="meta">Ephemeral · never persisted server-side.</div>
      </div>

      <label style={{ fontSize: 13 }}>
        Start with endpoint:{" "}
        <select value={endpoint} onChange={(e) => setEndpoint(e.target.value)}>
          <option>OS</option><option>PFS</option><option>NRM</option><option>relapse/progression</option>
        </select>
      </label>

      <label className="check">
        <input type="checkbox" checked={tc} onChange={(e) => setTc(e.target.checked)} />
        <span>
          I downloaded this dataset from CIBMTR and accept CIBMTR's Terms &amp; Conditions. I
          understand this is a research/educational tool, outputs are drafts for expert review,
          and <b>CIBMTR did not review or endorse</b> any analysis produced here.
        </span>
      </label>

      <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
        <button className="secondary" onClick={onBack}>← Back</button>
        <button disabled={!canRun} onClick={() => onStart({ tc, endpoint, dataset, dictionary })}>
          Run reproduction
        </button>
      </div>
      {!dataset && tc && (
        <div className="meta" style={{ marginTop: 8 }}>Attach the dataset file to enable the run.</div>
      )}
    </div>
  );
}
