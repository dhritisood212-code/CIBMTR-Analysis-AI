"""Generate a SCHEMA-FAITHFUL SYNTHETIC dataset shaped like the P-5297 analytic file.

    ############################################################################
    #  THIS IS NOT REAL CIBMTR DATA. It is randomly generated to exercise the   #
    #  pipeline headlessly without the T&C-gated real dataset. Any resemblance  #
    #  to real patients or to the published P-5297 numbers is coincidental.     #
    ############################################################################

The "published" target-results here are derived from a canonical analysis of THIS synthetic
cohort, so a correct reproduction matches within tolerance by construction. The point of this
example is to prove the cohort -> analyze -> compare -> verdict SPINE and the reproducibility-
class machinery end-to-end, not to validate the statistics (the r-engine unit tests do that).

Outputs (written next to this script):
  synthetic_P-5297.csv      analytic table (one row per subject)
  analytic.schema.yaml      sidecar mapping roles -> columns (per analytic-parquet.contract.md)
  target-results.yaml       "published" numbers + reproducibility classes (per the schema)
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd
import yaml
from lifelines import CoxPHFitter, KaplanMeierFitter, AalenJohansenFitter

HERE = pathlib.Path(__file__).resolve().parent
SEED = 20200101
N = 3000
TAU = 60  # administrative censoring (months)


def generate() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    age_grp = rng.choice(["<60", "60-69", ">=70"], size=N, p=[0.35, 0.35, 0.30])
    kps_grp = rng.choice(["<90", ">=90"], size=N, p=[0.40, 0.60])
    hctci_grp = rng.choice(["0", "1-2", ">=3"], size=N, p=[0.45, 0.35, 0.20])

    # Known linear predictors (log-hazard) - the "truth".
    age_beta = {"<60": 0.0, "60-69": 0.15, ">=70": 0.40}          # OS/PFS age effect
    kps_beta = {"<90": 0.20, ">=90": 0.0}
    hct_beta = {"0": 0.0, "1-2": 0.10, ">=3": 0.30}
    lp = np.array([age_beta[a] for a in age_grp]) + \
        np.array([kps_beta[k] for k in kps_grp]) + \
        np.array([hct_beta[h] for h in hctci_grp])

    # OS: exponential with baseline rate scaled by exp(lp).
    os_rate = 0.020 * np.exp(lp)
    t_os = rng.exponential(1.0 / os_rate)
    time_os = np.minimum(t_os, TAU)
    event_os = (t_os <= TAU).astype(int)

    # PFS: slightly higher hazard (progression happens before/with death).
    pfs_rate = 0.030 * np.exp(lp)
    t_pfs = rng.exponential(1.0 / pfs_rate)
    time_pfs = np.minimum(t_pfs, TAU)
    event_pfs = (t_pfs <= TAU).astype(int)

    # Competing risks on one clock: cause 1 = NRM, cause 2 = relapse.
    # Age raises relapse hazard more than NRM (a plausible pattern).
    nrm_rate = 0.006 * np.exp(0.5 * lp)
    rel_age = {"<60": 0.0, "60-69": 0.10, ">=70": 0.25}
    rel_rate = 0.020 * np.exp(np.array([rel_age[a] for a in age_grp]))
    t_nrm = rng.exponential(1.0 / nrm_rate)
    t_rel = rng.exponential(1.0 / rel_rate)
    t_first = np.minimum(t_nrm, t_rel)
    cause = np.where(t_nrm <= t_rel, 1, 2)
    time_cr = np.minimum(t_first, TAU)
    event_cr = np.where(t_first <= TAU, cause, 0).astype(int)

    return pd.DataFrame({
        "subject_id": [f"SYN{n:05d}" for n in range(N)],
        "age_grp": pd.Categorical(age_grp, categories=["<60", "60-69", ">=70"], ordered=True),
        "kps_grp": pd.Categorical(kps_grp, categories=["<90", ">=90"]),
        "hctci_grp": pd.Categorical(hctci_grp, categories=["0", "1-2", ">=3"]),
        "time_os": time_os.round(3), "event_os": event_os,
        "time_pfs": time_pfs.round(3), "event_pfs": event_pfs,
        "time_cr": time_cr.round(3), "event_cr": event_cr,
    })


def _cox_hr_ge70(df, time, event) -> dict:
    d = df.copy()
    d["age_60_69"] = (d["age_grp"] == "60-69").astype(int)
    d["age_ge70"] = (d["age_grp"] == ">=70").astype(int)
    d["kps_ge90"] = (d["kps_grp"] == ">=90").astype(int)
    d["hct_12"] = (d["hctci_grp"] == "1-2").astype(int)
    d["hct_ge3"] = (d["hctci_grp"] == ">=3").astype(int)
    cols = ["age_60_69", "age_ge70", "kps_ge90", "hct_12", "hct_ge3", time, event]
    fit = CoxPHFitter().fit(d[cols], time, event)
    hr = float(np.exp(fit.params_["age_ge70"]))
    lo, hi = np.exp(fit.confidence_intervals_.loc["age_ge70"].values)
    return {"point": round(hr, 3), "ci_low": round(float(lo), 3),
            "ci_high": round(float(hi), 3), "unit": "HR",
            "significance_verdict": "significant" if lo > 1 else "not-significant"}


def _km_median(df, time, event) -> float:
    km = KaplanMeierFitter().fit(df[time], df[event])
    return float(km.median_survival_time_)


def _cif_1yr(df, interest_code) -> float:
    aj = AalenJohansenFitter().fit(df["time_cr"], df["event_cr"], event_of_interest=interest_code)
    cd = aj.cumulative_density_
    at12 = cd[cd.index <= 12]
    return round(float(at12.iloc[-1, 0]) if len(at12) else 0.0, 3)


def build_targets(df: pd.DataFrame) -> dict:
    os_hr = _cox_hr_ge70(df, "time_os", "event_os")
    pfs_hr = _cox_hr_ge70(df, "time_pfs", "event_pfs")
    n_total = len(df)
    n_ge70 = int((df["age_grp"] == ">=70").sum())
    kps_ge90_pct = round(100 * float((df["kps_grp"] == ">=90").mean()), 1)

    def tgt(**kw):
        kw.setdefault("expected_divergence_direction", "either")
        return kw

    return {
        "study_id": "P-5297-SYNTHETIC",
        "table1_targets": [
            tgt(id="cohort_n_total", endpoint="cohort", quantity="Total analytic N",
                expected={"point": n_total, "unit": "count"},
                reproducibility_class="within-tolerance",
                class_reason="Cohort n from inclusion filters; +-5%."),
            tgt(id="cohort_n_ge70", endpoint="cohort", quantity="N in >=70 subgroup",
                expected={"point": n_ge70, "unit": "count"},
                reproducibility_class="within-tolerance",
                class_reason="Subgroup n from the age-category column; +-5%."),
            tgt(id="t1_kps_ge90", endpoint="table1", quantity="Proportion KPS >=90",
                expected={"point": kps_ge90_pct, "unit": "percent"},
                reproducibility_class="within-tolerance",
                class_reason="Baseline proportion; +-2-3 pts."),
        ],
        "targets": [
            tgt(id="os_median", endpoint="OS", quantity="Median OS",
                expected={"point": round(_km_median(df, "time_os", "event_os"), 1),
                          "unit": "months"},
                reproducibility_class="exact",
                class_reason="KM readout on the provided OS data."),
            tgt(id="os_hr_age_ge70", endpoint="OS",
                quantity="Adjusted HR, age >=70 vs <60",
                expected={**os_hr, "source_location": "synthetic canonical Cox"},
                reproducibility_class="within-tolerance",
                class_reason="Adjusted Cox HR; all covariates present in file -> +-10%."),
            tgt(id="pfs_median", endpoint="PFS", quantity="Median PFS",
                expected={"point": round(_km_median(df, "time_pfs", "event_pfs"), 1),
                          "unit": "months"},
                reproducibility_class="exact",
                class_reason="KM readout on the provided PFS data."),
            tgt(id="pfs_hr_age_ge70", endpoint="PFS",
                quantity="Adjusted HR, age >=70 vs <60 (PFS)",
                expected={**pfs_hr, "source_location": "synthetic canonical Cox"},
                reproducibility_class="within-tolerance",
                class_reason="Adjusted Cox HR; covariates present -> +-10%."),
            tgt(id="nrm_cif_1yr", endpoint="NRM", quantity="1-year NRM cumulative incidence",
                expected={"point": _cif_1yr(df, 1), "unit": "proportion"},
                reproducibility_class="within-tolerance",
                class_reason="CIF point estimate; +-0.02 absolute."),
            tgt(id="rel_cif_1yr", endpoint="relapse/progression",
                quantity="1-year relapse cumulative incidence",
                expected={"point": _cif_1yr(df, 2), "unit": "proportion"},
                reproducibility_class="within-tolerance",
                class_reason="CIF point estimate; +-0.02 absolute."),
            # The instructive coarsening example: file has age_grp only, not continuous age.
            tgt(id="os_hr_age_continuous", endpoint="OS",
                quantity="HR per 1-year age increase (continuous-age model)",
                expected={"point": 1.03, "unit": "HR",
                          "source_location": "hypothetical continuous-age model"},
                reproducibility_class="coarsening-limited",
                class_reason=("File provides age_grp only; a continuous-age HR cannot be "
                              "reproduced. Categorical-age model IS reproducible (see "
                              "os_hr_age_ge70)."),
                expected_divergence_direction="either"),
        ],
    }


def sidecar() -> dict:
    return {
        "subject_id": "subject_id",
        "exposure": {"role": "exposure", "column": "age_grp",
                     "levels": ["<60", "60-69", ">=70"], "reference": "<60"},
        "covariates": [
            {"role": "covariate", "name": "kps", "column": "kps_grp",
             "levels": ["<90", ">=90"], "reference": "<90"},
            {"role": "covariate", "name": "hct_ci", "column": "hctci_grp",
             "levels": ["0", "1-2", ">=3"], "reference": "0"},
        ],
        "endpoints": [
            {"name": "OS", "structure": "composite-survival",
             "time": "time_os", "event": "event_os"},
            {"name": "PFS", "structure": "composite-survival",
             "time": "time_pfs", "event": "event_pfs"},
            {"name": "NRM", "structure": "competing-risk", "time": "time_cr", "event": "event_cr",
             "event_codes": {"censored": 0, "nrm": 1, "relapse": 2}},
            {"name": "relapse", "structure": "competing-risk", "time": "time_cr",
             "event": "event_cr", "event_codes": {"censored": 0, "relapse": 2, "nrm": 1}},
        ],
    }


def main() -> None:
    df = generate()
    df.to_csv(HERE / "synthetic_P-5297.csv", index=False)
    (HERE / "analytic.schema.yaml").write_text(yaml.safe_dump(sidecar(), sort_keys=False))
    targets = build_targets(df)
    header = ("# SYNTHETIC target-results (NOT real CIBMTR/P-5297 numbers). Generated from a\n"
              "# canonical analysis of the synthetic cohort by make_synthetic_data.py.\n")
    (HERE / "target-results.yaml").write_text(header + yaml.safe_dump(targets, sort_keys=False))
    print(f"wrote synthetic_P-5297.csv (n={len(df)}), analytic.schema.yaml, target-results.yaml")
    print("published-target preview:")
    for t in targets["targets"]:
        print(f"  {t['id']:22} [{t['reproducibility_class']:18}] expected={t['expected'].get('point')}")


if __name__ == "__main__":
    main()
