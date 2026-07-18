"""Interface to the sandboxed R runtime.

Agent-produced R is UNTRUSTED code that touches user data, so it never runs in this process.
It runs via the sandbox command (see infra/README.md) which must enforce:
  * no network,
  * CPU / memory / wall-time limits,
  * a per-run ephemeral workspace mounted read-write only at the run dir,
  * the internal `cibmtrrepro` R package preinstalled.

This module shells out to that command and captures stdout/stderr/exit code. If the sandbox
command is not configured or not found, `require_sandbox()` raises a clear, actionable error -
the same "starts unconfigured, fails clearly at use" pattern as the Anthropic client.
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import get_settings


class RSandboxNotConfigured(RuntimeError):
    pass


class RExecutionError(RuntimeError):
    pass


@dataclass
class RResult:
    exit_code: int
    stdout: str
    stderr: str
    wall_seconds: float
    session_info: str | None = None


def require_sandbox() -> str:
    settings = get_settings()
    cmd = settings.r_sandbox_cmd
    resolved = (settings.repo_root / cmd) if not Path(cmd).is_absolute() else Path(cmd)
    if not resolved.exists() and shutil.which(cmd) is None:
        raise RSandboxNotConfigured(
            f"R sandbox command '{cmd}' not found. Agent-produced R cannot be executed.\n"
            "  -> Build the sandbox image and script per infra/README.md, then set "
            "R_SANDBOX_CMD in .env.\n"
            "Until then, the panel can produce the R artifact but cannot run it, so results "
            "(agent-results.yaml, match-report.md) cannot be generated."
        )
    return str(resolved if resolved.exists() else cmd)


def run_r_script(script_path: Path, run_dir: Path) -> RResult:
    """Execute one R script in the sandbox. Returns captured output; never raises on a
    non-zero exit (the caller decides what a failed run means) but raises if the sandbox
    itself is missing or times out."""
    cmd = require_sandbox()
    settings = get_settings()
    argv = [
        cmd,
        "--script", str(script_path),
        "--workdir", str(run_dir),
        "--timeout", str(settings.r_timeout_seconds),
        "--max-memory-mb", str(settings.r_max_memory_mb),
    ]
    import time
    start = time.monotonic()
    try:
        proc = subprocess.run(
            argv, capture_output=True, text=True,
            timeout=settings.r_timeout_seconds + 15,  # grace over the in-sandbox limit
        )
    except subprocess.TimeoutExpired as exc:
        raise RExecutionError(
            f"R sandbox exceeded {settings.r_timeout_seconds}s wall limit for "
            f"{script_path.name}."
        ) from exc
    wall = time.monotonic() - start
    session_info_path = run_dir / "sessionInfo.txt"
    session_info = session_info_path.read_text() if session_info_path.exists() else None
    return RResult(
        exit_code=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        wall_seconds=wall,
        session_info=session_info,
    )
