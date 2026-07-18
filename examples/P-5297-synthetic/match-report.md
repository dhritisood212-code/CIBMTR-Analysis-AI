---
study_id: P-5297-SYNTHETIC
run_id: 4acbc8b72685
generated_at: '2026-07-17T21:38:12.228920+00:00'
verdict: pass
table1_reconciled: true
summary:
  exact:
    matched: 2
    total: 2
  within-tolerance:
    matched: 7
    total: 7
  coarsening-limited:
    matched: 1
    total: 1
  not-reproducible:
    matched: 0
    total: 0
scores:
- target_id: cohort_n_total
  class: within-tolerance
  expected:
    point: 3000
    unit: count
  observed:
    point: 3000
    unit: count
  verdict: match
  reason: within +-5%
- target_id: cohort_n_ge70
  class: within-tolerance
  expected:
    point: 873
    unit: count
  observed:
    point: 873
    unit: count
  verdict: match
  reason: within +-5%
- target_id: t1_kps_ge90
  class: within-tolerance
  expected:
    point: 59.9
    unit: percent
  observed:
    point: 59.9
    unit: percent
  verdict: match
  reason: within +-3.0 percent
- target_id: os_median
  class: exact
  expected:
    point: 25.6
    unit: months
  observed:
    point: 25.6
    unit: months
  verdict: match
  reason: within +-2.0 months
- target_id: os_hr_age_ge70
  class: within-tolerance
  expected:
    point: 1.392
    ci_low: 1.26
    ci_high: 1.538
    unit: HR
    significance_verdict: significant
    source_location: synthetic canonical Cox
  observed:
    point: 1.392
    ci_low: 1.26
    ci_high: 1.538
    unit: HR
    significance_verdict: significant
  verdict: match
  reason: within 10%, same direction, same significance
- target_id: pfs_median
  class: exact
  expected:
    point: 17.1
    unit: months
  observed:
    point: 17.1
    unit: months
  verdict: match
  reason: within +-2.0 months
- target_id: pfs_hr_age_ge70
  class: within-tolerance
  expected:
    point: 1.51
    ci_low: 1.375
    ci_high: 1.658
    unit: HR
    significance_verdict: significant
    source_location: synthetic canonical Cox
  observed:
    point: 1.51
    ci_low: 1.375
    ci_high: 1.658
    unit: HR
    significance_verdict: significant
  verdict: match
  reason: within 10%, same direction, same significance
- target_id: nrm_cif_1yr
  class: within-tolerance
  expected:
    point: 0.076
    unit: proportion
  observed:
    point: 0.076
    unit: proportion
  verdict: match
  reason: within +-0.02 proportion
- target_id: rel_cif_1yr
  class: within-tolerance
  expected:
    point: 0.22
    unit: proportion
  observed:
    point: 0.22
    unit: proportion
  verdict: match
  reason: within +-0.02 proportion
- target_id: os_hr_age_continuous
  class: coarsening-limited
  expected:
    point: 1.03
    unit: HR
    source_location: hypothetical continuous-age model
  observed: null
  verdict: behaved-as-predicted
  reason: not computed - coarsened variable unavailable, exactly as flagged up front
---

# Match report — P-5297 (SYNTHETIC)

> Input is a synthetic, schema-faithful stand-in for the T&C-gated public file. Numbers are not real CIBMTR/P-5297 results.

**Verdict: `pass`**  ·  Table 1 reconciled: **True**

| Target | Class | Expected | Observed | Verdict | Why |
|---|---|---|---|---|---|
| cohort_n_total | within-tolerance | 3000 count | 3000 count | **match** | within +-5% |
| cohort_n_ge70 | within-tolerance | 873 count | 873 count | **match** | within +-5% |
| t1_kps_ge90 | within-tolerance | 59.9 percent | 59.9 percent | **match** | within +-3.0 percent |
| os_median | exact | 25.6 months | 25.6 months | **match** | within +-2.0 months |
| os_hr_age_ge70 | within-tolerance | 1.392 HR (95% CI 1.26–1.538) | 1.392 HR (95% CI 1.26–1.538) | **match** | within 10%, same direction, same significance |
| pfs_median | exact | 17.1 months | 17.1 months | **match** | within +-2.0 months |
| pfs_hr_age_ge70 | within-tolerance | 1.51 HR (95% CI 1.375–1.658) | 1.51 HR (95% CI 1.375–1.658) | **match** | within 10%, same direction, same significance |
| nrm_cif_1yr | within-tolerance | 0.076 proportion | 0.076 proportion | **match** | within +-0.02 proportion |
| rel_cif_1yr | within-tolerance | 0.22 proportion | 0.22 proportion | **match** | within +-0.02 proportion |
| os_hr_age_continuous | coarsening-limited | 1.03 HR | — | **behaved-as-predicted** | not computed - coarsened variable unavailable, exactly as flagged up front |

Reproducibility classes were assigned by the Interpreter *before* analysis; the scorer reads them and never upgrades a class. The `os_hr_age_continuous` target is `coarsening-limited` and is correctly reported as an interpretable non-reproduction, not a failure.
