# `analytic.parquet` contract

The **single most important contract** in the system: the Cohort Builder (2a) and the Cohort
Assembler (2b) both emit a file with **this identical schema**, so the Analyst's R code is
agnostic to which agent produced it. Provenance is recorded in `agent-results.yaml`
(`cohort.produced_by`), not in the data's shape.

## Required structure

One row per analytic subject (one transplant episode). Required columns:

| Column | Type | Meaning |
|---|---|---|
| `subject_id` | string | Stable, de-identified id from the public file. |
| `<exposure>` | factor/int | The main exposure, coded exactly as `study-spec.exposure.coding` says (e.g. `age_grp` as an ordered factor `<60 / 60-69 / >=70`). Column name recorded in a sidecar (below). |
| `<covariate_i>` | per spec | One column per entry in `study-spec.covariates`, coded per its `coding`. |
| `time_<endpoint>` | double | Follow-up time (months) for each endpoint, from `study-spec.endpoints[].time_origin`. |
| `event_<endpoint>` | int | Event indicator. For `competing-risk` endpoints this is a **multi-state code**: `0 = censored`, `1 = event of interest`, `2 = competing event` (extend `3..k` if the spec lists more competing events, in the order listed). For `composite-survival` endpoints: `0/1`. |

## Sidecar: `analytic.schema.yaml`

Written alongside the parquet so column *names* (which vary by study) map to their *roles*
(which don't). The Analyst reads roles, never hardcoded column names.

```yaml
subject_id: subject_id
exposure:
  role: exposure
  column: age_grp
  levels: ["<60", "60-69", ">=70"]
  reference: "<60"
covariates:
  - {role: covariate, name: kps, column: kps_grp, levels: ["<90", ">=90"]}
  - {role: covariate, name: hct_ci, column: hctci_grp, levels: ["0", "1-2", ">=3"]}
endpoints:
  - {name: OS,  structure: composite-survival, time: time_os,  event: event_os}
  - {name: PFS, structure: composite-survival, time: time_pfs, event: event_pfs}
  - {name: NRM, structure: competing-risk, time: time_nrm, event: event_nrm, event_codes: {censored: 0, nrm: 1, relapse: 2}}
  - {name: relapse, structure: competing-risk, time: time_rel, event: event_rel, event_codes: {censored: 0, relapse: 1, nrm: 2}}
```

## Invariants (validated by `backend/app/core/contracts.py`)

1. Every role/column in the sidecar exists in the parquet.
2. No `NA` in any `time_*` or `event_*` column for included rows (attrition must have removed
   them; document in `attrition.md`).
3. Competing-risk `event_*` values are within the declared `event_codes` set.
4. Row count is within `cohort n ±5%` of `target-results` cohort target *or* the mismatch is
   surfaced (the Comparator checks Table 1 first for exactly this reason).
5. Factor `levels`/`reference` match `study-spec` exactly, so HR reference levels align with
   the paper.
