"""In-memory run registry for the MVP. Swap for Redis/Postgres in production (see TODO)."""
from __future__ import annotations

import threading
import uuid

from .models import RunState

_lock = threading.Lock()
_runs: dict[str, RunState] = {}


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def put(state: RunState) -> None:
    with _lock:
        _runs[state.run_id] = state


def get(run_id: str) -> RunState | None:
    with _lock:
        return _runs.get(run_id)


def all_runs() -> list[RunState]:
    with _lock:
        return list(_runs.values())
