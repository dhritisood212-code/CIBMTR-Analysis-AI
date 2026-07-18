"""Run-state data model shared by the orchestrator, API, and CLI."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class Stage(str, Enum):
    INTERPRET = "interpret"
    BUILD_COHORT = "build_cohort"
    ASSEMBLE_COHORT = "assemble_cohort"
    ANALYZE = "analyze"
    COMPARE = "compare"
    DIAGNOSE = "diagnose"
    DONE = "done"


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    NEEDS_INPUT = "needs_input"   # e.g. awaiting T&C confirmation / dataset upload
    PASSED = "passed"
    PARTIAL = "partial"
    FAILED = "failed"
    ERROR = "error"               # infrastructure error (no key, sandbox down, etc.)


class StageEvent(BaseModel):
    stage: Stage
    status: str                    # "started" | "completed" | "error"
    at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    detail: str | None = None
    artifact: str | None = None    # filename written in this stage


class RunRequest(BaseModel):
    study_id: str
    # Path to the user's session dataset + dictionary (uploaded, ephemeral). Links-only
    # catalog means the SERVER never fetches these; the user provides them for their session.
    dataset_path: str | None = None
    dictionary_path: str | None = None
    tc_confirmed: bool = False     # user accepted CIBMTR Terms & Conditions
    primary_endpoint: str | None = None   # start narrow (e.g. "OS"), then widen
    # New-study mode: user supplies their own plan, no published target.
    new_study_plan: str | None = None


class RunState(BaseModel):
    run_id: str
    study_id: str
    status: RunStatus = RunStatus.QUEUED
    stage: Stage = Stage.INTERPRET
    iteration: int = 0
    events: list[StageEvent] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)   # filenames in runs/<run_id>/
    verdict: str | None = None                            # from match-report front matter
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def record(self, stage: Stage, status: str, detail: str | None = None,
               artifact: str | None = None) -> None:
        self.events.append(StageEvent(stage=stage, status=status, detail=detail,
                                      artifact=artifact))
        self.stage = stage
        if artifact and artifact not in self.artifacts:
            self.artifacts.append(artifact)
