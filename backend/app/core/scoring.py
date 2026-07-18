"""Deterministic reference scorer.

Implements the tolerance + reproducibility-class rules from schemas/match-report.contract.md
as pure functions. Two uses:

  1. Headless proof runs (examples/) score agent-results against target-results without an LLM.
  2. In production it double-checks the Comparator AGENT's Markdown against a mechanical scorer,
     so the human-readable report and the machine verdict can never silently disagree.

The class is READ from target-results (assigned up front by the Interpreter); this scorer never
chooses or upgrades a class - that is the anti-tuning invariant.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .config import Tolerances, get_tolerances


@dataclass
class TargetScore:
    target_id: str
    reproducibility_class: str
    expected: dict
    observed: dict | None
    verdict: str          # match | mismatch | behaved-as-predicted | not-scored | cannot-assess
    reason: str


@dataclass
class ScoreReport:
    verdict: str          # pass | partial | fail
    table1_reconciled: bool
    scores: list[TargetScore] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


def _within_hr(expected: dict, observed: dict, tol: Tolerances) -> tuple[bool, str]:
    e, o = expected.get("point"), observed.get("point")
    if e is None or o is None:
        return False, "missing HR point estimate"
    rel = abs(o - e) / abs(e)
    if rel > tol.hr_rel:
        return False, f"HR off by {rel:.0%} (> {tol.hr_rel:.0%})"
    # same direction relative to 1.0
    if (e - 1.0) * (o - 1.0) < 0:
        return False, "HR on the opposite side of 1.0 (direction flip)"
    # same significance verdict, when both provided
    es, os_ = expected.get("significance_verdict"), observed.get("significance_verdict")
    if es and os_ and es != os_ and "not-reported" not in (es, os_):
        return False, f"significance verdict differs ({es} vs {os_})"
    return True, f"within {tol.hr_rel:.0%}, same direction, same significance"


def _within_rel(expected: dict, observed: dict, tol: float, unit: str) -> tuple[bool, str]:
    e, o = expected.get("point"), observed.get("point")
    if e is None or o is None:
        return False, f"missing {unit} value"
    if e == 0:
        return (o == 0), "exact zero" if o == 0 else "expected 0"
    rel = abs(o - e) / abs(e)
    return (rel <= tol), (f"within +-{tol:.0%}" if rel <= tol else f"off by {rel:.0%} (> {tol:.0%})")


def _within_abs(expected: dict, observed: dict, tol: float, unit: str) -> tuple[bool, str]:
    e, o = expected.get("point"), observed.get("point")
    if e is None or o is None:
        return False, f"missing {unit} point estimate"
    if abs(o - e) > tol:
        return False, f"{unit} off by {abs(o - e):.3g} (> {tol})"
    return True, f"within +-{tol} {unit}"


def _pick_abs_tol(unit: str, tol: Tolerances) -> float:
    unit = (unit or "").lower()
    if unit in ("proportion", "cif", "km"):
        return tol.cif_km_abs
    if unit in ("months", "month"):
        return tol.median_months
    if unit in ("percent", "pct", "points", "pts"):
        return tol.table1_prop_pts * 100
    return tol.cif_km_abs


def score_target(expected: dict, observed: dict | None, rclass: str,
                 divergence_dir: str | None, tol: Tolerances) -> tuple[str, str]:
    """Return (verdict, reason) for one target, given its PRE-ASSIGNED class."""
    if rclass == "not-reproducible":
        return "not-scored", "not-reproducible by design (info absent from file/paper)"

    if observed is None or observed.get("point") is None:
        if rclass == "coarsening-limited":
            return ("behaved-as-predicted",
                    "not computed - coarsened variable unavailable, exactly as flagged up front")
        return "cannot-assess", "no observed value produced by the analysis"

    unit = (expected.get("unit") or observed.get("unit") or "").lower()
    if unit == "hr":
        ok, why = _within_hr(expected, observed, tol)
    elif unit == "count":
        ok, why = _within_rel(expected, observed, tol.cohort_n_rel, "count")
    else:
        ok, why = _within_abs(expected, observed, _pick_abs_tol(unit, tol), unit or "value")

    if rclass in ("exact", "within-tolerance"):
        return ("match", why) if ok else ("mismatch", why)

    if rclass == "coarsening-limited":
        # We do NOT expect an exact match; check the divergence behaves as predicted.
        e, o = expected["point"], observed["point"]
        if divergence_dir in ("higher", "lower"):
            went = "higher" if o > e else "lower"
            if went == divergence_dir:
                return "behaved-as-predicted", f"diverged {went}, as predicted"
            return "mismatch", f"diverged {went}, opposite to predicted {divergence_dir}"
        return ("behaved-as-predicted" if not ok else "match",
                "divergence consistent with the known coarsening")
    return "cannot-assess", f"unknown class '{rclass}'"


def score(target_results: dict, agent_results: dict,
          table1_reconciled: bool | None = None,
          tol: Tolerances | None = None) -> ScoreReport:
    tol = tol or get_tolerances()
    observed_by_id = {r["target_id"]: r.get("observed") for r in agent_results.get("results", [])}

    # Table 1 first: reconcile cohort/table1 targets unless caller already decided.
    t1_targets = target_results.get("table1_targets", [])
    if table1_reconciled is None:
        table1_reconciled = True
        for t in t1_targets:
            v, _ = score_target(t.get("expected", {}), observed_by_id.get(t["id"]),
                                t["reproducibility_class"],
                                t.get("expected_divergence_direction"), tol)
            if v == "mismatch":
                table1_reconciled = False

    scores: list[TargetScore] = []
    for t in t1_targets + target_results.get("targets", []):
        v, why = score_target(t.get("expected", {}), observed_by_id.get(t["id"]),
                              t["reproducibility_class"],
                              t.get("expected_divergence_direction"), tol)
        scores.append(TargetScore(
            target_id=t["id"], reproducibility_class=t["reproducibility_class"],
            expected=t.get("expected", {}), observed=observed_by_id.get(t["id"]),
            verdict=v, reason=why,
        ))

    # Verdict rule (matches the contract).
    hard = [s for s in scores if s.reproducibility_class in ("exact", "within-tolerance")]
    soft = [s for s in scores if s.reproducibility_class in
            ("coarsening-limited", "not-reproducible")]
    hard_ok = all(s.verdict == "match" for s in hard)
    soft_ok = all(s.verdict in ("behaved-as-predicted", "not-scored") for s in soft)

    if not table1_reconciled:
        verdict = "fail"
    elif hard_ok and soft_ok:
        verdict = "pass"
    elif any(s.verdict == "match" for s in hard):
        verdict = "partial"
    else:
        verdict = "fail"

    summary = {
        "exact": _tally(scores, "exact"),
        "within-tolerance": _tally(scores, "within-tolerance"),
        "coarsening-limited": _tally(scores, "coarsening-limited"),
        "not-reproducible": _tally(scores, "not-reproducible"),
    }
    return ScoreReport(verdict=verdict, table1_reconciled=table1_reconciled,
                       scores=scores, summary=summary)


def _tally(scores: list[TargetScore], rclass: str) -> dict:
    rows = [s for s in scores if s.reproducibility_class == rclass]
    good = sum(1 for s in rows if s.verdict in ("match", "behaved-as-predicted", "not-scored"))
    return {"matched": good, "total": len(rows)}
