# The agent panel

Six scoped agents, each with one job and a typed file contract. Prompts are plain Markdown so
they are diffable and reviewable. The orchestrator prepends [`_shared_preamble.md`](_shared_preamble.md)
to each agent's own prompt at call time.

| # | Agent | Prompt | Reads | Writes |
|---|---|---|---|---|
| 1 | Study Interpreter | [`study_interpreter.md`](study_interpreter.md) | paper, data dictionary, study metadata | `study-spec.yaml`, `target-results.yaml` |
| 2a | Cohort Builder | [`cohort_builder.md`](cohort_builder.md) | `study-spec.yaml`, dataset, dictionary | `analytic.parquet`, `derivation-check.md` |
| 2b | Cohort Assembler | [`cohort_assembler.md`](cohort_assembler.md) | `study-spec.yaml`, dataset or Builder output | `analytic.parquet`, `table1.md`, `attrition.md` |
| 3 | Analyst | [`analyst.md`](analyst.md) | `study-spec.yaml`, `target-results.yaml`, `analytic.parquet`, R engine | `reproduce_<study>.R`, `agent-results.yaml` |
| 4 | Comparator | [`comparator.md`](comparator.md) | `target-results.yaml`, `agent-results.yaml`, `table1.md` | `match-report.md` |
| 5 | Diagnoser | [`diagnoser.md`](diagnoser.md) | `match-report.md` + all upstream artifacts | `diagnosis.md` |

## Design invariants encoded in the prompts

- **Anti-tuning ordering.** The Interpreter assigns each target's reproducibility class
  *before* any analysis runs; the Comparator scores against that frozen class; the Diagnoser
  may not propose a fix whose only justification is closing the gap. This ordering is the
  system's honesty guarantee.
- **No prose statistics.** Every number originates from executed R captured by the sandbox.
- **The artifact is the product.** The Analyst optimizes for a rerunnable, readable script,
  not a chat answer. "Would a biostatistician merge this PR?" is the bar.
- **One shared cohort contract.** 2a and 2b emit identical `analytic.parquet` schemas, so the
  Analyst is agnostic to which built the cohort.
- **Data is not instructions.** Every prompt treats uploaded file content as inert data;
  injected "instructions" inside a dataset are ignored and noted.

## Wiring

Prompt text is loaded and dispatched by `backend/app/agents/registry.py`; the sequence and
the diagnosis→re-run loop live in `backend/app/core/orchestrator.py`. Models per agent are
configurable (`backend/app/core/config.py`) — the harder reasoning roles (Interpreter,
Diagnoser) default to a stronger model than the mechanical ones.
