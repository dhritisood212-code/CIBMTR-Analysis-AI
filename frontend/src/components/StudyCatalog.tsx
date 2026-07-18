import type { StudyCatalogEntry } from "../types";

/** Catalog cards: metadata + links ONLY. No dataset is hosted here. */
export function StudyCatalog({
  studies,
  onPick,
}: {
  studies: StudyCatalogEntry[];
  onPick: (s: StudyCatalogEntry) => void;
}) {
  return (
    <div className="panel">
      <h2>Study catalog</h2>
      <div className="row">
        {studies.map((s) => (
          <div className="card" key={s.study_id}>
            <h3>{s.study_id} · {s.cibmtr_study_number}</h3>
            <div className="meta">{s.working_committee}</div>
            <p style={{ fontSize: 13, margin: "8px 0" }}>{s.title}</p>
            <div className="meta">{s.citation}{s.pmid ? ` · PMID ${s.pmid}` : ""}</div>
            <div style={{ display: "flex", gap: 10, margin: "10px 0", fontSize: 12 }}>
              <a href={s.manuscript_url} target="_blank" rel="noreferrer">Manuscript</a>
              <a href={s.dataset_download_url} target="_blank" rel="noreferrer">Dataset (CIBMTR)</a>
              <a href={s.data_dictionary_url} target="_blank" rel="noreferrer">Data dictionary</a>
            </div>
            <button onClick={() => onPick(s)}>Start a reproduction →</button>
          </div>
        ))}
      </div>
    </div>
  );
}
