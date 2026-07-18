"""Tests for the deterministic reference scorer, including the negative cases the headless
pass-run doesn't exercise (mismatch detection, direction flips, anti-tuning class discipline)."""
from app.core.scoring import score, score_target
from app.core.config import get_tolerances

TOL = get_tolerances()


def _t(id, cls, expected, div=None):
    return {"id": id, "endpoint": "x", "quantity": "q", "reproducibility_class": cls,
            "class_reason": "r", "expected": expected, "expected_divergence_direction": div}


def test_within_tolerance_hr_matches():
    v, _ = score_target({"point": 1.40, "unit": "HR", "significance_verdict": "significant"},
                        {"point": 1.45, "unit": "HR", "significance_verdict": "significant"},
                        "within-tolerance", None, TOL)
    assert v == "match"


def test_hr_outside_band_mismatches():
    v, _ = score_target({"point": 1.40, "unit": "HR"},
                        {"point": 1.90, "unit": "HR"}, "within-tolerance", None, TOL)
    assert v == "mismatch"


def test_hr_direction_flip_mismatches():
    v, why = score_target({"point": 1.05, "unit": "HR"},
                          {"point": 0.98, "unit": "HR"}, "within-tolerance", None, TOL)
    assert v == "mismatch" and "1.0" in why


def test_significance_flip_mismatches():
    v, _ = score_target({"point": 1.10, "unit": "HR", "significance_verdict": "significant"},
                        {"point": 1.10, "unit": "HR", "significance_verdict": "not-significant"},
                        "within-tolerance", None, TOL)
    assert v == "mismatch"


def test_exact_class_cannot_be_softened():
    # An 'exact' target that misses is a mismatch - the scorer never relabels it.
    v, _ = score_target({"point": 24.0, "unit": "months"},
                        {"point": 30.0, "unit": "months"}, "exact", None, TOL)
    assert v == "mismatch"


def test_coarsening_limited_not_computed_is_ok():
    v, _ = score_target({"point": 1.03, "unit": "HR"}, None, "coarsening-limited", None, TOL)
    assert v == "behaved-as-predicted"


def test_table1_mismatch_forces_fail_even_if_endpoints_match():
    targets = {
        "study_id": "s",
        "table1_targets": [_t("n", "within-tolerance", {"point": 1000, "unit": "count"})],
        "targets": [_t("os_hr", "within-tolerance", {"point": 1.4, "unit": "HR"})],
    }
    agent = {"results": [
        {"target_id": "n", "observed": {"point": 700, "unit": "count"}, "source": "x"},   # -30%
        {"target_id": "os_hr", "observed": {"point": 1.42, "unit": "HR"}, "source": "y"},
    ]}
    rep = score(targets, agent, tol=TOL)
    assert rep.table1_reconciled is False
    assert rep.verdict == "fail"   # Table 1 didn't reconcile -> fail regardless of the HR


def test_full_pass_when_everything_in_band():
    targets = {
        "study_id": "s",
        "table1_targets": [_t("n", "within-tolerance", {"point": 1000, "unit": "count"})],
        "targets": [
            _t("os_hr", "within-tolerance", {"point": 1.4, "unit": "HR",
                                             "significance_verdict": "significant"}),
            _t("cont", "coarsening-limited", {"point": 1.03, "unit": "HR"}),
        ],
    }
    agent = {"results": [
        {"target_id": "n", "observed": {"point": 1020, "unit": "count"}, "source": "x"},
        {"target_id": "os_hr", "observed": {"point": 1.45, "unit": "HR",
                                            "significance_verdict": "significant"}, "source": "y"},
        {"target_id": "cont", "observed": None,
         "not_computed_reason": "coarsened"},
    ]}
    rep = score(targets, agent, tol=TOL)
    assert rep.verdict == "pass" and rep.table1_reconciled is True
