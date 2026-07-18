# `r-engine/` — the internal `cibmtrrepro` R package (STUB)

The **durable asset**. A small, unit-tested R package with canonical implementations of the
standard CIBMTR endpoints/models. The Analyst calls these rather than re-implementing models
inline, so every reproduction shares one validated core. Reproductions are this package's test
suite: each new study either passes using shared components or exposes a gap in them.

> Status: **implemented** (Milestone 1). All functions below are real implementations wrapping
> `survival`/`cmprsk`, with exact-match `testthat` tests on synthetic data in
> `tests/testthat/`. See "Running the tests" and "How this was verified" below.

## Canonical function contract

Composite-survival (OS/DFS/PFS/GRFS):

```r
km_fit(data, time, event, strata = NULL)          # Kaplan-Meier; returns fit + median table
logrank_test(data, time, event, group)            # log-rank
cox_ph(data, time, event, covariates, ref = list())  # Cox PH; returns tidy HR table
```

Competing-risk (relapse/NRM/GVHD/engraftment):

```r
cif(data, time, event_code, codes)                # cumulative incidence (Aalen-Johansen)
grays_test(data, time, event_code, group, codes)  # Gray's test
finegray_model(data, time, event_code, covariates, codes)      # Fine-Gray subdistribution
cause_specific_cox(data, time, event_code, cause, covariates)  # cause-specific Cox
```

Marginal-only fallback (when only published KM curves are available, no IPD):

```r
ipd_from_km(curve_points, at_risk_table)          # wraps IPDfromKM
```

Every function: deterministic given a seed, returns a **tidy tibble** the Analyst can write to
`results/*.csv` and read into `agent-results.yaml`, and is covered by exact-match unit tests on
small synthetic inputs (`tests/testthat/`). The package **is** the place statistics live; the
agent loop orchestrates, it does not compute.

## Layout

```
r-engine/
├── DESCRIPTION
├── NAMESPACE
├── R/
│   ├── survival.R          # km_fit, logrank_test, cox_ph
│   ├── competing_risk.R    # cif, grays_test, finegray_model, cause_specific_cox
│   ├── fallback.R          # ipd_from_km (IPDfromKM wrapper)
│   └── synthetic.R         # synth_survival, synth_competing (deterministic test data)
└── tests/
    ├── testthat.R
    └── testthat/test-endpoints.R   # exact-match tests on synthetic data
```

## Running the tests

```r
# from r-engine/
install.packages(c("survival", "cmprsk", "testthat"))   # + IPDfromKM if using the fallback
devtools::load_all(".")        # or R CMD INSTALL .
testthat::test_dir("tests/testthat")
# or: R CMD check .
```

## How this was verified

R is not runnable in the environment where this package was written, so the numeric
expectations baked into the tests were **independently cross-checked in Python**
(`lifelines` / `AalenJohansenFitter`) on the same synthetic designs, and the R sources passed a
static delimiter-balance check:

| Test assertion | Independent check |
|---|---|
| `km_fit` median on times 1..10 = **5** | lifelines `KaplanMeierFitter.median_survival_time_` = 5.0 |
| `cif` CIF₁(t=3)=**0.4**, CIF₁(t=5)=**0.8** on the hand dataset | `AalenJohansenFitter` = 0.4 / 0.8 exactly |
| `cox_ph` recovers HR **1.6** (CI contains truth) | lifelines Cox: 1.62, CI (1.52, 1.73) |
| `cause_specific_cox` recovers HR **1.5** with competing events censored | lifelines Cox on cause-1-as-event: 1.49, CI (1.43, 1.56) |
| `grays_test` significant for differing group CIFs | group CIF₁ separates 0.80 vs 0.95 at n=5000 |

The tests assert recovery of a **known simulation truth** (not a hardcoded fitted value), so
they remain valid under R's own RNG. Running `testthat` in a real R install is the final
verification step (see `docs/TODO.md`).
