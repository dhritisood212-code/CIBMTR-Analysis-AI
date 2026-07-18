# `diagnosis.md` contract

Written by the **Diagnoser** when the `match-report.md` verdict is `fail` (or `partial` when
the orchestrator is configured to iterate on partials). It localizes each unexplained
mismatch and proposes a fix.

## Required content per mismatched target

```yaml
---
run_id: <uuid>
iteration: 1
diagnoses:
  - target_id: os_hr_age_ge70
    localized_to: cohort-assembler        # method-spec | cohort-builder | cohort-assembler
    hypothesis: "Table 1 shows our >=70 group is 1,780 vs the paper's ~2,092; we excluded
                 rows with missing KPS that the paper retained via a 'missing' category."
    grounded_in: "Methods, p.5079: 'KPS was modeled with a missing indicator category.'"
    proposed_fix: "Add a 'missing' level to kps_grp in the Assembler filter rather than
                   dropping those rows."
    predicted_effect: "Cohort n rises toward target; HR expected to move toward 1.42."
    forbidden_reason_check: passed        # see rule
---
```

## The one hard rule (anti-tuning)

Every proposed fix **must carry a reason grounded in the paper or the data dictionary**. A
fix whose only justification is "it makes the number closer to the target" is **forbidden**
and must be rejected by the Diagnoser itself (`forbidden_reason_check: failed` → the fix is
not emitted). The orchestrator also rejects any diagnosis whose `grounded_in` is empty or
whose `proposed_fix` references the target value.

## Loop control

The Diagnoser proposes; the orchestrator applies the fix by **re-running the relevant agent
with the correction in its input context** (it does not let the Diagnoser silently edit
another agent's artifact). `target-results.yaml` and its classes are **never** modified by the
loop. Max iterations and which agent to re-invoke are set in `backend/app/core/config.py`.
