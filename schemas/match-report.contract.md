# `match-report.md` contract

Written by the **Comparator**. Human-readable, but with a fixed front-matter block so it is
also machine-parseable and can be aggregated across runs into the catalog of what CIBMTR
public data can and can't reproduce.

## Required YAML front matter

```yaml
---
study_id: P-5297
run_id: <uuid>
generated_at: <iso8601>
verdict: pass | partial | fail          # see rule below
table1_reconciled: true | false          # Table 1 is checked FIRST
summary:
  exact:              {matched: N, total: N}
  within-tolerance:   {matched: N, total: N}
  coarsening-limited: {behaved-as-predicted: N, total: N}
  not-reproducible:   {total: N}
scores:
  - target_id: os_hr_age_ge70
    class: within-tolerance          # the PRE-ASSIGNED class from target-results.yaml
    expected: {point: 1.42, ci: [1.10, 1.83], unit: HR}
    observed: {point: 1.45, ci: [1.12, 1.88], unit: HR}
    verdict: match                    # match | mismatch | behaved-as-predicted | cannot-assess
    reason: "Within +-10% and same direction + same significance verdict."
---
```

## Body

Prose, organized **Table 1 first**, then endpoints grouped by reproducibility class. Each
target: class (color-coded in the UI), expected vs observed, verdict, and reason. The reason
must let a reader understand *why* — e.g. "we reproduce OS exactly; we cannot reproduce the
continuous-age model because the public file bins age, as flagged up front."

## `verdict` rule (must match the brief's pass bar)

- `pass` — all `exact` and `within-tolerance` targets matched **after Table 1 reconciled**,
  AND all `coarsening-limited` / `not-reproducible` targets behaved as their class predicted.
- `partial` — Table 1 reconciled and some but not all in-tolerance targets matched.
- `fail` — Table 1 did not reconcile, or an `exact`/`within-tolerance` target missed with no
  class-predicted explanation. Triggers the Diagnoser.

## Anti-tuning invariant

The Comparator **reads the class from `target-results.yaml`** and must not recompute or
"upgrade" it. If a target labelled `exact` misses, the verdict is `mismatch` — the Comparator
cannot relabel it `within-tolerance` to make it pass. Reclassification proposals go to the
Diagnoser, grounded in the paper/dictionary, and would require a fresh Interpreter pass.
