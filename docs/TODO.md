# Done vs. needs-productionization

## Done in this session (agents + orchestrator focus)

- Monorepo scaffold + top-level README (architecture, reproducibility-class model, compliance).
- **Typed file contracts** (`schemas/`): JSON Schema for study-spec, target-results,
  agent-results, the reproducibility-class enum; Markdown contracts for analytic.parquet,
  match-report, derivation-check, diagnosis; worked P-5297 examples (with numeric targets left
  as `CONFIRM_FROM_PMC`, not invented).
- **Six scoped agent system prompts** + shared preamble, encoding the anti-tuning ordering,
  no-prose-statistics rule, the shared cohort contract, and instruction-in-data defense.
- **FastAPI orchestrator** sequencing all six agents over a per-run working dir, with:
  - real Anthropic wiring (`anthropic_client.py`), configurable per-agent models, and a clear
    "not configured" error path;
  - contract validation between stages (`contracts.py`) incl. a fabrication check;
  - a sandboxed-R runner interface (`r_runner.py`) with a clear "sandbox not configured" error;
  - the diagnosis→re-run loop with `target-results.yaml` immutability;
  - `POST /runs` API entry point and a `reproduce` CLI, sharing one orchestrator;
  - study catalog (links only) + T&C gate + session-data purge.

## R engine (Milestone 1 — the durable asset) — IMPLEMENTED

`cibmtrrepro` is implemented: km_fit, logrank_test, cox_ph, cif, grays_test, finegray_model,
cause_specific_cox, ipd_from_km, plus deterministic synthetic-data generators, all with
exact-match `testthat` tests. Expected values were cross-validated in Python (see
`r-engine/README.md` → "How this was verified").

Remaining for this component: **run `testthat` in a real R install** (R was not runnable in the
build environment) and wire `renv.lock` pinning. This is the one open verification step for the
engine.

## Milestone 2 (one study, end-to-end, headless) — SPINE PROVEN (synthetic)

`examples/P-5297-synthetic/` runs the full cohort → analyze → compare → verdict flow against a
schema-faithful **synthetic** stand-in for the T&C-gated public file, with no API key or R
sandbox needed. It produces a golden `reproduce_P-5297.R`, an `agent-results.yaml`, and a real
`match-report.md` that **passes**, with the coarsening-limited continuous-age target correctly
reported as `behaved-as-predicted`. A deterministic reference scorer (`backend/app/core/
scoring.py`, 8 unit tests) backs it and double-checks the Comparator agent in production.

Remaining to reach a real P-5297 reproduction: (1) run `reproduce_P-5297.R` in a real R install
against the sandbox; (2) have the Interpreter fill `target-results.yaml` from the PMC full text
(the `CONFIRM_FROM_PMC` values); (3) supply a live API key so the agent panel (not the Python
mirror) drives the run. The contracts and class machinery are already exercised.

## Needs productionization

**End-to-end proof on P-5297.** Wire the panel to actually reproduce OS via Cox first, then
PFS/NRM/relapse; confirm the Interpreter's `CONFIRM_FROM_PMC` values against the PMC full text;
produce a real `reproduce_P-5297.R` + `match-report.md`.

**Sandbox — MVP DONE; hardening open.** `infra/run_r_sandboxed.sh` is a real runner (timeout +
ulimit + ephemeral workspace + `Rscript --vanilla` + best-effort `unshare --net`), and the
backend image installs R + `cibmtrrepro`, so agent R executes. Verify live with `GET /r-health`.
Still open: container-per-run isolation (`--network none`, read-only rootfs, non-root, cgroup
limits) or gVisor/Firecracker for a hostile-input production posture; and wiring the session
**dataset upload** (frontend input -> backend upload endpoint -> cohort agents) so a real study,
not just the synthetic example, can run through the UI.

**Frontend — BUILT (MVP).** Vite + React + TS app in `frontend/`: study catalog, compliance
gate, run-progress timeline, and the artifact viewer (Table 1 first, color-coded reproducibility
classes, R script view, bundle download). Type-checks and builds clean; has a demo mode that
renders the real `examples/P-5297-synthetic` outputs with no backend. Remaining: wire the
session-scoped file upload to a real upload endpoint, swap run polling for SSE/websocket
streaming, add R syntax highlighting, and build the new-study-mode variant of the setup form.

**Orchestrator robustness.** Persist run state (Redis/Postgres) instead of in-memory `store`;
stream stage events (SSE/websocket) instead of poll; make the diagnosis loop apply
cohort-level fixes (re-run `_cohort`) behind an operator flag; add retries/backoff on API
calls; token/cost budgets per run.

**Auth & rate limiting.** Anonymous sessions are fine for MVP, but cap concurrent runs, R
CPU-seconds, and API spend since the app executes code and calls the model.

**Catalog growth.** Move the hardcoded catalog to a versioned store; add each new study as a
new R-engine test case (Milestone 4). Persist every `match-report.md` into the cross-study
"what public data can/can't reproduce" catalog.

**New-study mode.** Same engine, user-supplied plan, no target (Milestone 5) — plumbing exists
(`RunRequest.new_study_plan`); the Analyst path for target-less drafting needs its own prompt
branch and the Comparator skipped.
