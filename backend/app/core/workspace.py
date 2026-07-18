"""Per-run working directory.

Two storage tiers, per the compliance requirement:
  * SESSION data (the user's dataset + dictionary) is ephemeral: staged under a session dir
    and deleted on session end / TTL. NEVER persisted server-side beyond the session.
  * RUN artifacts (the R script, tables, match-report, session info) persist under runs/,
    and are git-committed per run for history/diffs/rollback. Source data is never committed.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .config import get_settings

# Files that are safe to persist/commit. A dataset must never land here.
ARTIFACT_ALLOWLIST = {
    "study-spec.yaml",
    "target-results.yaml",
    "derivation-check.md",
    "analytic.schema.yaml",     # schema sidecar only - NOT analytic.parquet (derived data)
    "table1.md",
    "attrition.md",
    "agent-results.yaml",
    "match-report.md",
    "diagnosis.md",
    "sessionInfo.txt",
    "renv.lock",
}
# reproduce_<study>.R and results/*.csv|png are also artifacts (matched by pattern below).


class Workspace:
    def __init__(self, run_id: str):
        self.run_id = run_id
        settings = get_settings()
        self.run_dir = settings.runs_dir / run_id
        self.session_dir = self.run_dir / "_session"   # ephemeral, .gitignored, TTL-deleted
        self.results_dir = self.run_dir / "results"
        for d in (self.run_dir, self.session_dir, self.results_dir):
            d.mkdir(parents=True, exist_ok=True)
        (self.run_dir / ".gitignore").write_text("_session/\nanalytic.parquet\n")

    # --- session (ephemeral) ---
    def stage_dataset(self, src: Path, name: str) -> Path:
        dst = self.session_dir / name
        shutil.copy2(src, dst)
        return dst

    def purge_session(self) -> None:
        """Delete the user's source data. Called on session end / TTL / run finalize."""
        if self.session_dir.exists():
            shutil.rmtree(self.session_dir, ignore_errors=True)

    # --- artifacts (persistent) ---
    def write_artifact(self, name: str, content: str) -> Path:
        path = self.run_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def read_artifact(self, name: str) -> str:
        return (self.run_dir / name).read_text()

    def has(self, name: str) -> bool:
        return (self.run_dir / name).exists()

    def commit(self, message: str) -> None:
        """Git-commit the run's artifacts (best-effort; no-op if git unavailable)."""
        try:
            subprocess.run(["git", "add", "-A", str(self.run_dir)],
                           check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", message, "--", str(self.run_dir)],
                           check=True, capture_output=True)
        except Exception:  # noqa: BLE001 - versioning is best-effort, not load-bearing
            pass
