// Mirrors the backend contracts (backend/app/core/models.py, schemas/match-report.contract.md).

export type ReproClass =
  | "exact"
  | "within-tolerance"
  | "coarsening-limited"
  | "not-reproducible";

export type Verdict = "pass" | "partial" | "fail";

export interface StudyCatalogEntry {
  study_id: string;
  cibmtr_study_number: string;
  working_committee: string;
  title: string;
  citation: string;
  doi?: string;
  pmid?: string;
  manuscript_url: string;
  dataset_download_url: string;
  data_dictionary_url: string;
  terms_url: string;
  note: string;
}

export interface StageEvent {
  stage: string;
  status: "started" | "completed" | "error";
  at: string;
  detail?: string | null;
  artifact?: string | null;
}

export type RunStatus =
  | "queued"
  | "running"
  | "needs_input"
  | "passed"
  | "partial"
  | "failed"
  | "error";

export interface RunState {
  run_id: string;
  study_id: string;
  status: RunStatus;
  stage: string;
  iteration: number;
  events: StageEvent[];
  artifacts: string[];
  verdict?: Verdict | null;
  error?: string | null;
  created_at: string;
}

// Parsed from the match-report.md YAML front matter.
export interface TargetScore {
  target_id: string;
  class: ReproClass;
  expected: Record<string, unknown> | null;
  observed: Record<string, unknown> | null;
  verdict: "match" | "mismatch" | "behaved-as-predicted" | "not-scored" | "cannot-assess";
  reason: string;
}

export interface MatchReport {
  study_id: string;
  run_id: string;
  generated_at: string;
  verdict: Verdict;
  table1_reconciled: boolean;
  summary: Record<ReproClass, { matched?: number; total: number }>;
  scores: TargetScore[];
  body: string; // markdown after the front matter
}
