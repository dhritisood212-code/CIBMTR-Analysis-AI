// Typed client for the orchestrator API (backend/app/api/routes.py) + match-report parsing.
import yaml from "js-yaml";
import { API_BASE } from "./config";
import type { MatchReport, RunState, StudyCatalogEntry } from "./types";

export interface StartRunBody {
  study_id: string;
  tc_confirmed: boolean;
  primary_endpoint?: string;
  new_study_plan?: string;
  dataset?: File; // the CIBMTR dataset (.zip) the user downloaded under T&C
  dictionary?: File; // the data dictionary (.xlsx/.rtf)
}

// Prefix every path with the configured backend base (empty in dev -> Vite proxy).
export const url = (path: string) => `${API_BASE}${path}`;

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}: ${await r.text()}`);
  return r.json() as Promise<T>;
}

export const api = {
  listStudies: () => fetch(url("/studies")).then((r) => j<StudyCatalogEntry[]>(r)),
  getStudy: (id: string) => fetch(url(`/studies/${id}`)).then((r) => j<StudyCatalogEntry>(r)),
  startRun: (body: StartRunBody) => {
    // multipart/form-data so we can attach the dataset + dictionary files. Do NOT set
    // Content-Type manually — the browser adds the multipart boundary.
    const fd = new FormData();
    fd.append("study_id", body.study_id);
    fd.append("tc_confirmed", String(body.tc_confirmed));
    if (body.primary_endpoint) fd.append("primary_endpoint", body.primary_endpoint);
    if (body.new_study_plan) fd.append("new_study_plan", body.new_study_plan);
    if (body.dataset) fd.append("dataset", body.dataset);
    if (body.dictionary) fd.append("dictionary", body.dictionary);
    return fetch(url("/runs"), { method: "POST", body: fd }).then((r) => j<RunState>(r));
  },
  getRun: (runId: string) => fetch(url(`/runs/${runId}`)).then((r) => j<RunState>(r)),
  getArtifact: (runId: string, name: string) =>
    fetch(url(`/runs/${runId}/artifacts/${name}`)).then((r) => {
      if (!r.ok) throw new Error(`artifact ${name}: ${r.status}`);
      return r.text();
    }),
};

/** Split a Markdown artifact into its YAML front matter and body. */
export function splitFrontMatter(md: string): { meta: Record<string, unknown>; body: string } {
  const t = md.replace(/^﻿/, "");
  if (!t.trimStart().startsWith("---")) return { meta: {}, body: md };
  const rest = t.slice(t.indexOf("---") + 3);
  const end = rest.indexOf("\n---");
  if (end === -1) return { meta: {}, body: md };
  const fm = rest.slice(0, end);
  const body = rest.slice(end + 4);
  return { meta: (yaml.load(fm) as Record<string, unknown>) ?? {}, body };
}

/** Parse a match-report.md into a typed MatchReport. */
export function parseMatchReport(md: string): MatchReport {
  const { meta, body } = splitFrontMatter(md);
  return { ...(meta as unknown as MatchReport), body };
}
