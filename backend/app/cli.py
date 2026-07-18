"""Developer CLI entry point: `reproduce <study> --data ... --dict ...`.

Same orchestrator the API uses, run synchronously in the foreground so a developer can watch
the stages and inspect the artifact bundle in runs/<run_id>/.
"""
from __future__ import annotations

import argparse
import sys

from .core.catalog import CATALOG
from .core.models import RunRequest
from .core.orchestrator import Orchestrator
from .core.store import new_run_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="reproduce",
        description="Reproduce a published CIBMTR study from its public dataset.",
    )
    parser.add_argument("study_id", help=f"Catalog study id, e.g. {', '.join(CATALOG)}")
    parser.add_argument("--data", dest="dataset_path",
                        help="Path to the session dataset you downloaded from CIBMTR (under T&C).")
    parser.add_argument("--dict", dest="dictionary_path", help="Path to the data dictionary (.xlsx).")
    parser.add_argument("--endpoint", dest="primary_endpoint",
                        help="Start with a single primary endpoint, e.g. OS.")
    parser.add_argument("--accept-tc", action="store_true",
                        help="Confirm you have accepted CIBMTR's Terms & Conditions for this data.")
    args = parser.parse_args(argv)

    if not args.accept_tc:
        print("Refusing to run: pass --accept-tc to confirm you downloaded the dataset from "
              "CIBMTR and accepted CIBMTR's Terms & Conditions. This tool never fetches or "
              "hosts the data for you.", file=sys.stderr)
        return 2

    req = RunRequest(
        study_id=args.study_id,
        dataset_path=args.dataset_path,
        dictionary_path=args.dictionary_path,
        primary_endpoint=args.primary_endpoint,
        tc_confirmed=True,
    )
    run_id = new_run_id()
    print(f"[run {run_id}] reproducing {args.study_id} ...")
    state = Orchestrator(req, run_id).run()

    for ev in state.events:
        line = f"  {ev.stage.value:16} {ev.status:10}"
        if ev.artifact:
            line += f" -> {ev.artifact}"
        if ev.detail:
            line += f"   ({ev.detail})"
        print(line)

    print(f"\n[run {run_id}] status={state.status.value} verdict={state.verdict}")
    if state.error:
        print(f"ERROR: {state.error}", file=sys.stderr)
    print(f"Artifacts in: runs/{run_id}/")
    return 0 if state.status.value in {"passed", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
