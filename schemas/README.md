# Typed file contracts

Every agent reads the previous agent's output from the per-run working directory
(`runs/<run_id>/`) and writes its own. The contracts here are what makes the panel a
pipeline rather than a chat: each file has a fixed shape, so the next agent (and the
orchestrator's validators) can rely on it.

| File | Producer | Consumer(s) | Schema |
|---|---|---|---|
| `study-spec.yaml` | Interpreter | Builder, Assembler, Analyst | [`study-spec.schema.json`](study-spec.schema.json) |
| `target-results.yaml` | Interpreter | Comparator | [`target-results.schema.json`](target-results.schema.json) |
| `derivation-check.md` | Builder | human, Diagnoser | prose + a required results table (see [`derivation-check.contract.md`](derivation-check.contract.md)) |
| `analytic.parquet` | Builder **or** Assembler | Analyst | [`analytic-parquet.contract.md`](analytic-parquet.contract.md) |
| `table1.md` | Assembler | Comparator | prose table (see contract in Assembler prompt) |
| `attrition.md` | Assembler | human, Comparator | prose (waterfall) |
| `reproduce_<study>.R` | Analyst | human, R sandbox | executable R (readability is an acceptance criterion) |
| `agent-results.yaml` | Analyst | Comparator | [`agent-results.schema.json`](agent-results.schema.json) |
| `match-report.md` | Comparator | human, Diagnoser | [`match-report.contract.md`](match-report.contract.md) |
| `diagnosis.md` | Diagnoser | Orchestrator, human | [`diagnosis.contract.md`](diagnosis.contract.md) |

## Shared enums

The reproducibility class is a shared, closed enum used across `target-results.yaml`,
`agent-results.yaml`, and `match-report.md`:

```
exact | within-tolerance | coarsening-limited | not-reproducible
```

Defined once in [`reproducibility-class.schema.json`](reproducibility-class.schema.json) and
`$ref`'d by the others.

## Validation

`backend/app/core/contracts.py` loads these JSON Schemas and validates each agent's output
before the next agent runs. A malformed artifact halts the run with a contract error rather
than silently corrupting downstream steps.

## Worked example

[`examples/P-5297.study-spec.yaml`](examples/P-5297.study-spec.yaml) and
[`examples/P-5297.target-results.yaml`](examples/P-5297.target-results.yaml) show the
Interpreter's expected output shape for the Milestone-1 study. **Numeric target values in the
example are placeholders** marked `TODO_FROM_PMC` — the Interpreter fills them by reading the
PMC full text at run time; they are deliberately not invented here.
