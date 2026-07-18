# CIBMTR Reproduction Panel

A public research/educational tool that reproduces the results of published CIBMTR
studies from CIBMTR's public analysis datasets, then serves as a reusable analysis
engine for biostatisticians on new studies.

**The product is the artifact, not the chat.** Every run produces a clean, commented,
version-controlled R script a biostatistician can read, rerun, and edit — plus results
tables and a machine-readable match report. Agents draft and check; the human owns the
final.

> **Not medical advice. Not a clinical or regulatory instrument.** Outputs are drafts for
> expert review. This tool does not host, bundle, or redistribute CIBMTR datasets — see
> [Data & compliance](#data--compliance).

---

## This session's scope

This repo was built to a specific depth: **the six-agent panel and the orchestrator**,
with the Anthropic API wired for real (erroring cleanly when unconfigured). The R engine
and frontend are present as documented stubs with stable interfaces so the panel can be
completed around them.

| Area | Status in this repo |
|---|---|
| `schemas/` — typed file contracts between agents | **Built** (this session) |
| `agents/` — the six scoped system prompts | **Built** (this session) |
| `backend/` — FastAPI orchestrator, Anthropic client, run model, R-runner interface, CLI | **Built** (this session) |
| `r-engine/` — tested internal R package | **Stub** with interface + test skeleton; needs Milestone-1 build |
| `frontend/` — React artifact viewer | **Stub** with the view contract documented |
| `infra/` — sandbox + run scripts | **Stub** with the sandbox contract documented |

See [`docs/TODO.md`](docs/TODO.md) for the explicit "done vs. needs-productionization" split.

---

## Architecture

```
                          ┌─────────────────────────────────────────────┐
  React frontend  ──POST──▶  FastAPI orchestrator  (backend/app)         │
  (artifact viewer)         │                                            │
                            │   per-run working directory (ephemeral)    │
                            │   runs/<run_id>/                           │
                            │     ├── study-spec.yaml       (Interpreter)│
                            │     ├── target-results.yaml   (Interpreter)│
                            │     ├── derivation-check.md    (Builder)   │
                            │     ├── analytic.parquet       (Builder|Assembler)
                            │     ├── table1.md / attrition.md (Assembler)│
                            │     ├── reproduce_<study>.R    (Analyst)   │
                            │     ├── agent-results.yaml     (Analyst)   │
                            │     ├── match-report.md        (Comparator)│
                            │     └── diagnosis.md           (Diagnoser) │
                            │                                            │
                            │   each agent = one Anthropic API call with │
                            │   a scoped system prompt (agents/*.md)     │
                            │                                            │
                            │   Analyst/Builder R  ──▶  sandboxed R      │
                            │                          runtime (infra/)  │
                            └─────────────────────────────────────────────┘
```

The **Orchestrator** sequences the agents and exposes a single entry point:
`POST /runs` (frontend) and `reproduce <study>` (CLI). Each agent reads the previous
agent's typed output from the per-run working directory and writes its own. **No agent
computes a statistic in prose** — every number comes from executed R.

### The six agents

1. **Study Interpreter** — reads the paper (or user-supplied methods + target numbers) and
   emits `study-spec.yaml` + `target-results.yaml`. **Before anything runs, it assigns each
   target quantity a reproducibility class** (see below) by reading the methods against the
   data dictionary. This up-front commitment is the anti-tuning safeguard.
2. **Cohort Builder (2a)** — constructs the cohort *from scratch* by deriving
   endpoints/covariates from raw component fields; where the public file also carries the
   pre-computed derived variable, it re-derives and checks against that column
   (`derivation-check.md`). Its full from-raw-*registry* path is **unvalidated** until
   raw-registry access exists; only its derivation logic is (partially) validated today.
3. **Cohort Assembler (2b)** — takes the cohort (Builder output *or* the file's pre-computed
   variables), applies final analytic filters, emits `analytic.parquet` + `table1.md` +
   `attrition.md`. **2a and 2b share one contract:** an identical `analytic.parquet` schema,
   so downstream code is agnostic to which produced it.
4. **Analyst** — runs exactly the paper's methods in R. **Its primary output is the
   artifact:** a clean, self-contained, commented `reproduce_<study>.R`, plus
   `agent-results.yaml`. Estimator is chosen by the estimand, not by preference.
5. **Comparator** — scores agent results against published numbers using each target's
   **pre-assigned** class. **Checks Table 1 first.** Emits `match-report.md`.
6. **Diagnoser** — on mismatch, localizes the cause (method spec / derivation / final
   filtering) and proposes a fix that **must carry a reason grounded in the paper or
   dictionary** — never "it made the number closer." Loops back.

Each agent's contract and prompt live in [`agents/`](agents/) and [`schemas/`](schemas/).

---

## Reproducibility classes (a first-class concept)

The Interpreter tags every target quantity **up front, before any analysis runs**:

| Class | Meaning | Example |
|---|---|---|
| `exact` | should match to the decimal | median OS from KM on the provided data |
| `within-tolerance` | match within a band | adjusted HR ±10%; CIF ±0.02 |
| `coarsening-limited` | can't match exactly; a needed variable was coarsened/removed; expect known-direction divergence | any model with a **center random effect** (center IDs stripped from public files); exact-date-dependent analyses |
| `not-reproducible` | required info isn't in the file or the paper | method given only as "adjusted for relevant covariates," final model not stated |

Committing the class *before* results is what keeps the loop honest and prevents
tuning-to-target. Non-reproduction is an **interpretable finding**, not a bare fail
("we reproduce OS exactly; we cannot reproduce the NRM model because it used a center
random effect stripped from the public file"). Every run's `match-report.md` is persisted so
that, across many studies, they accumulate into a catalog of what CIBMTR public data can and
can't reproduce.

### Default tolerances (configurable — see `backend/app/core/config.py`)

cohort n ±5% · Table 1 proportions ±2–3 pts · median survival ±1–2 mo · CIF/KM point
estimate ±0.02 absolute · HR ±10% relative **and** same direction + same significance
verdict. A run **passes** when all `exact`/`within-tolerance` targets match after Table 1
reconciles, and all `coarsening-limited`/`not-reproducible` targets behave as their class
predicted.

---

## The artifact bundle (deliverable of every run)

- `reproduce_<study>.R` — deterministic (seed set), self-contained, commented (each modeling
  choice references the paper's methods).
- results tables + figures, regenerated by rerunning the script.
- `match-report.md` — versioned record of what reproduced and why, by class.
- `renv.lock` / `sessionInfo()` — locked environment so it reruns identically later.
- The bundle is downloadable and git-committed per run (history / diffs / rollback).

**Acceptance bar for the script:** *would a biostatistician merge this as a PR?* Readability
is an explicit acceptance criterion, not an afterthought.

---

## Milestone-1 target study

Built against one deliberately-clean study first (autologous setting: no GVHD, no donor/HLA
matching, no center random effect; single main exposure; four standard endpoints; a
spreadsheet data dictionary).

- **Study:** "Age no bar: A CIBMTR analysis of elderly patients undergoing autologous
  hematopoietic cell transplantation for multiple myeloma." Munshi PN et al., *Cancer*
  2020;126(23):5077–5087. DOI 10.1002/cncr.33171. **PMID 32965680** (free PMC full text).
- **CIBMTR study #:** MM18-03a · **Working Committee:** Plasma Cell Disorders · **Dataset ID:** P-5297.
- Manuscript page, dataset zip, and data dictionary links are captured in
  [`agents/study_interpreter.md`](agents/study_interpreter.md) as the Interpreter's ground truth.

The app stores only study **metadata and links**. Users fetch the dataset themselves from
CIBMTR under CIBMTR's Terms & Conditions.

---

## Running it

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env          # then set ANTHROPIC_API_KEY

# CLI (developer entry point)
reproduce P-5297 --data /path/to/P-5297.zip --dict /path/to/MM18-03---data-dictionary.xlsx

# API (frontend entry point)
uvicorn app.main:app --reload
# POST /runs   with the session dataset + chosen study id
```

Without `ANTHROPIC_API_KEY` the app starts but any run fails fast with a clear message
(see `backend/app/core/anthropic_client.py`). Without a configured R sandbox, runs fail at
the execution step with an equally clear message (see `infra/README.md`).

**Model names** are configurable and not hardcoded to a single version. Defaults are read
from env (`INTERPRETER_MODEL`, `ANALYST_MODEL`, …); check <https://docs.claude.com> for the
current model list before pinning production values.

---

## Data & compliance

- **Do not host, bundle, or redistribute CIBMTR datasets.** This app stores only study
  metadata and links. Users fetch each dataset themselves from CIBMTR and must accept
  CIBMTR's Terms & Conditions; the UI surfaces the link and a confirmation step before a
  session can use data.
- User-provided data is **ephemeral and session-scoped** — deleted on session end. Source
  data is never persisted server-side. Only run *artifacts and match reports* persist.
- This is a **research and educational secondary-analysis tool**, not a clinical or
  regulatory instrument, and not medical advice.
- The product communicates honest limits: `coarsening-limited` results are expected to
  diverge; the Cohort Builder's from-raw-registry path is unvalidated; center-effect models
  generally can't be reproduced from public files.
- Results ship with the CIBMTR public-dataset acknowledgment text and a clear statement that
  **CIBMTR did not review or endorse the analysis** (see [`docs/COMPLIANCE.md`](docs/COMPLIANCE.md)).
- **Agents never execute instructions found inside an uploaded file or dataset** — those are
  data, not commands. This is enforced in every agent prompt and in the orchestrator's
  message construction.

---

## Repo layout

```
cibmtr-repro/
├── agents/        the six scoped system prompts (+ shared preamble)
├── backend/       FastAPI orchestrator, Anthropic client, run model, R runner, CLI
├── schemas/       typed file contracts (YAML/JSON Schema) exchanged between agents
├── r-engine/      internal R package (STUB: interface + test skeleton)
├── frontend/      React artifact viewer (STUB: view contract)
├── infra/         sandboxed R runtime (STUB: sandbox contract)
└── docs/          COMPLIANCE, TODO, ARCHITECTURE notes
```

## Explicitly out of scope

Gates/sign-off tiers, multiplicity correction, "improve on the published method," and
form-version governance. These belong to a future new-study-rigor layer owned by the human
biostatistician. This tool is firmly **aid, don't replace**.
