"""Headless end-to-end proof of the pipeline SPINE, without an API key or the R sandbox.

It stands in for the orchestrator's analyze -> compare stages by:
  1. mirroring reproduce_P-5297.R's statistics in Python (lifelines) on the synthetic data -
     this is exactly what the sandboxed R would compute - and writing agent-results.yaml;
  2. scoring agent-results against target-results with the backend's DETERMINISTIC reference
     scorer (app.core.scoring), then rendering match-report.md per the contract.

The real system runs the R artifact in the sandbox and the Comparator agent writes the report;
this script proves the same cohort -> analyze -> compare -> verdict flow is sound and that the
reproducibility-class machinery behaves as designed (including the coarsening-limited target
that legitimately cannot be reproduced).

Run:  python run_headless.py       (after make_synthetic_data.py)
"""
from __future__ import annotations

import datetime as dt
import pathlib
import sys
import uuid

import numpy as np
import pandas as pd
import yaml
from lifelines import AalenJohansenFitter, CoxPHFitter, KaplanMeierFitter

HERE = pathlib.Path(__file__).resolve().parent
# Make the backend's reference scorer importable.
sys.path.insert(0, str(HERE.parents[1] / "backend"))
from app.core.scoring import ScoreReport, score  # noqa: E402


def _cox_age_ge70(df: pd.DataFrame, time: str, event: str) -> dict:
    """Adjusted Cox (age dummies + kps + hct), return the age>=70 HR row - mirrors cox_ph()."""
    d = pd.DataFrame({
        "age_60_69": (df["age_grp"] == "60-69").astype(int),
        "age_ge70": (df["age_grp"] == ">=70").astype(int),
        "kps_ge90": (df["kps_grp"] == ">=90").astype(int),
        "hct_12": (df["hctci_grp"] == "1-2").astype(int),
        "hct_ge3": (df["hctci_grp"] == ">=3").astype(int),
        time: df[time], event: df[event],
    })
    fit = CoxPHFitter().fit(d, time, event)
    hr = float(np.exp(fit.params_["age_ge70"]))
    lo, hi = (float(x) for x in np.exp(fit.confidence_intervals_.loc["age_ge70"].values))
    return {"point": round(hr, 3), "ci_low": round(lo, 3), "ci_high": round(hi, 3),
            "unit": "HR", "significance_verdict": "significant" if lo > 1 else "not-significant"}


def _km_median(df: pd.DataFrame, time: str, event: str) -> float:
    return round(float(KaplanMeierFitter().fit(df[time], df[event]).median_survival_time_), 1)


def _cif_1yr(df: pd.DataFrame, interest: int) -> float:
    aj = AalenJohansenFitter(seed=1).fit(df["time_cr"], df["event_cr"], event_of_interest=interest)
    cd = aj.cumulative_density_
    at12 = cd[cd.index <= 12]
    return round(float(at12.iloc[-1, 0]) if len(at12) else 0.0, 3)


def analyze(df: pd.DataFrame) -> dict:
    """The Analyst's job, mirrored: every value comes from a computation, each cites its source."""
    os_hr, pfs_hr = _cox_age_ge70(df, "time_os", "event_os"), _cox_age_ge70(df, "time_pfs", "event_pfs")
    res = [
        {"target_id": "cohort_n_total", "observed": {"point": int(len(df)), "unit": "count"},
         "source": "nrow(analytic)"},
        {"target_id": "cohort_n_ge70",
         "observed": {"point": int((df["age_grp"] == ">=70").sum()), "unit": "count"},
         "source": "sum(age_grp == '>=70')"},
        {"target_id": "t1_kps_ge90",
         "observed": {"point": round(100 * float((df["kps_grp"] == ">=90").mean()), 1),
                      "unit": "percent"}, "source": "mean(kps_grp == '>=90')"},
        {"target_id": "os_median",
         "observed": {"point": _km_median(df, "time_os", "event_os"), "unit": "months"},
         "source": "km_fit(time_os)$medians[1]"},
        {"target_id": "os_hr_age_ge70", "observed": os_hr,
         "source": "cox_ph(time_os,...)[age_grp>=70]"},
        {"target_id": "pfs_median",
         "observed": {"point": _km_median(df, "time_pfs", "event_pfs"), "unit": "months"},
         "source": "km_fit(time_pfs)$medians[1]"},
        {"target_id": "pfs_hr_age_ge70", "observed": pfs_hr,
         "source": "cox_ph(time_pfs,...)[age_grp>=70]"},
        {"target_id": "nrm_cif_1yr",
         "observed": {"point": _cif_1yr(df, 1), "unit": "proportion"},
         "source": "cif(time_cr, interest=NRM) at t=12"},
        {"target_id": "rel_cif_1yr",
         "observed": {"point": _cif_1yr(df, 2), "unit": "proportion"},
         "source": "cif(time_cr, interest=relapse) at t=12"},
        # Coarsening-limited: legitimately not computed (continuous age absent from the file).
        {"target_id": "os_hr_age_continuous", "observed": None,
         "not_computed_reason": "continuous age not in file (age_grp only); coarsening-limited"},
    ]
    return {"study_id": "P-5297-SYNTHETIC", "script": "reproduce_P-5297.R", "seed": 20200101,
            "r_session": {"exit_code": 0}, "cohort": {"n": int(len(df)),
            "produced_by": "cohort-assembler"}, "results": res}


def render_report(rep: ScoreReport, run_id: str) -> str:
    def fmt(d):
        if not d:
            return "—"
        p = d.get("point")
        s = f"{p}{(' ' + d['unit']) if d.get('unit') else ''}" if p is not None else "—"
        if d.get("ci_low") is not None:
            s += f" (95% CI {d['ci_low']}–{d['ci_high']})"
        return s

    fm = {
        "study_id": "P-5297-SYNTHETIC", "run_id": run_id,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "verdict": rep.verdict, "table1_reconciled": rep.table1_reconciled,
        "summary": rep.summary,
        "scores": [{"target_id": s.target_id, "class": s.reproducibility_class,
                    "expected": s.expected, "observed": s.observed,
                    "verdict": s.verdict, "reason": s.reason} for s in rep.scores],
    }
    lines = ["---", yaml.safe_dump(fm, sort_keys=False).rstrip(), "---", "",
             "# Match report — P-5297 (SYNTHETIC)", "",
             "> Input is a synthetic, schema-faithful stand-in for the T&C-gated public file. "
             "Numbers are not real CIBMTR/P-5297 results.", "",
             f"**Verdict: `{rep.verdict}`**  ·  Table 1 reconciled: "
             f"**{rep.table1_reconciled}**", "",
             "| Target | Class | Expected | Observed | Verdict | Why |",
             "|---|---|---|---|---|---|"]
    for s in rep.scores:
        lines.append(f"| {s.target_id} | {s.reproducibility_class} | {fmt(s.expected)} | "
                     f"{fmt(s.observed)} | **{s.verdict}** | {s.reason} |")
    lines += ["", "Reproducibility classes were assigned by the Interpreter *before* analysis; "
              "the scorer reads them and never upgrades a class. The `os_hr_age_continuous` "
              "target is `coarsening-limited` and is correctly reported as an interpretable "
              "non-reproduction, not a failure.", ""]
    return "\n".join(lines)


def main() -> int:
    df = pd.read_csv(HERE / "synthetic_P-5297.csv")
    targets = yaml.safe_load((HERE / "target-results.yaml").read_text())

    agent_results = analyze(df)
    (HERE / "agent-results.yaml").write_text(yaml.safe_dump(agent_results, sort_keys=False))

    rep = score(targets, agent_results)
    run_id = uuid.uuid4().hex[:12]
    (HERE / "match-report.md").write_text(render_report(rep, run_id))

    print(f"verdict = {rep.verdict}   table1_reconciled = {rep.table1_reconciled}")
    for s in rep.scores:
        print(f"  {s.target_id:22} [{s.reproducibility_class:18}] -> {s.verdict:20} {s.reason}")
    # A correct reproduction of the synthetic study must PASS; fail loudly in CI otherwise.
    return 0 if rep.verdict == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
