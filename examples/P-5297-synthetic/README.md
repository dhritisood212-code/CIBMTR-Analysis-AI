# Milestone-2 spine proof — P-5297 (SYNTHETIC)

This example proves the pipeline **spine** end-to-end — cohort → analyze → compare → verdict —
and the reproducibility-class machinery, **without** an Anthropic API key, the R sandbox, or
the real (Terms-&-Conditions-gated) CIBMTR dataset.

> ⚠️ **The data here is synthetic.** `synthetic_P-5297.csv` is randomly generated to match the
> *shape* of the P-5297 analytic file. It is **not** real CIBMTR data and its numbers are **not**
> the published P-5297 results. The app never hosts real CIBMTR data; users download that
> themselves under CIBMTR's T&C.

## What's here

| File | Role |
|---|---|
| `make_synthetic_data.py` | Generates the schema-faithful mock with a **known truth**, plus `analytic.schema.yaml` and `target-results.yaml` (the "published" numbers + reproducibility classes, derived from a canonical analysis of the mock). |
| `synthetic_P-5297.csv` | The generated analytic table (age_grp / kps_grp / hctci_grp + OS/PFS/competing-risk time+event columns). |
| `analytic.schema.yaml` | Sidecar mapping roles → columns (per `schemas/analytic-parquet.contract.md`). |
| `target-results.yaml` | Expected values + frozen reproducibility classes (per `schemas/target-results.schema.json`). |
| `reproduce_P-5297.R` | **The golden artifact** — the clean, commented R script the Analyst agent is expected to produce. Uses the `cibmtrrepro` engine; runs in the R sandbox on the real system. |
| `run_headless.py` | Mirrors the R analysis in Python (lifelines) and runs the backend's deterministic scorer, so the whole spine executes here and is verifiable. Writes `agent-results.yaml` + `match-report.md`. |
| `agent-results.yaml`, `match-report.md` | Generated outputs of the headless run. |

## Run it

```bash
pip install lifelines pyyaml pandas
python make_synthetic_data.py     # -> csv, sidecar, target-results.yaml
python run_headless.py            # -> agent-results.yaml, match-report.md ; prints the verdict
```

Expected result: **`verdict = pass`**, Table 1 reconciled, every `exact`/`within-tolerance`
target matched, and the `os_hr_age_continuous` target reported as **`behaved-as-predicted`** —
the built-in coarsening example (the file has `age_grp` only, so a continuous-age HR
legitimately can't be reproduced; the categorical-age HR can).

## Why a synthetic study still proves something

The statistics themselves are validated by the `r-engine` unit tests. This example validates
the **orchestration**: that roles flow through the sidecar, that competing-risk endpoints share
one clock, that results are produced only from computation (each carries a `source`), that the
scorer honors the **pre-assigned** classes and never upgrades one to force a pass, and that
Table 1 is checked first. Because the mock's "published" targets come from a canonical analysis
of the same data, a *correct* reproduction matches within tolerance by construction — so any
future regression in the spine shows up as a failed run.

## Relationship to the real P-5297 run

On the real study, three things change and nothing else: (1) the input is the dataset the user
downloaded from CIBMTR under T&C; (2) `target-results.yaml` is written by the **Interpreter**
from the PMC full text (with the `CONFIRM_FROM_PMC` values filled in); (3) `reproduce_P-5297.R`
runs in the hardened **R sandbox** and the **Comparator agent** writes `match-report.md` (which
the deterministic scorer here double-checks). The contracts, roles, and class machinery are
identical.
