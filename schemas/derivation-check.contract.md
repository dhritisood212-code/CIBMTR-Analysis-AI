# `derivation-check.md` contract

Written by the **Cohort Builder (2a)** whenever the public file contains **both** the raw
component fields **and** a pre-computed derived variable. The Builder re-derives from the raw
components and checks its output against the file's own column. This is the only part of the
Builder that is validated today; its full from-raw-*registry* path is unvalidated until
raw-registry access exists.

## Required content

For each derived variable the Builder reconstructs (e.g. an endpoint event indicator, HCT-CI,
DRI, event times):

1. **What was derived** and from which raw columns (cite the data dictionary).
2. **The derivation rule**, in words and as the R expression used.
3. **Agreement table** against the file's pre-computed column:

   | Derived variable | n agree | n disagree | % agree | disagreement pattern |
   |---|---|---|---|---|
   | `event_nrm` | 2088 | 4 | 99.8% | 4 rows where relapse and death share a date |

4. **Disagreement diagnosis** — for every disagreement, a grounded explanation (tie-breaking
   rule, rounding, a documented coding convention in the dictionary). "Close enough" is not an
   acceptable explanation; either the rule is understood or it is flagged.
5. **Verdict:** `validated` (agreement within tolerance and disagreements understood) or
   `flagged` (unexplained disagreement — surfaced to the Diagnoser and the human; the run may
   fall back to the file's pre-computed column with that choice recorded).

## Why this exists

It converts the Builder's from-scratch derivation into a *checkable* claim. Where the file
gives us the answer key (its own derived column), we grade the Builder against it and report
the grade honestly, rather than trusting either blindly.
