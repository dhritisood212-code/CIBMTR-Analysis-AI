"""HTTP surface. The frontend calls exactly one entry point to start a run (`POST /runs`) and
polls `GET /runs/{id}`; the artifact viewer reads files via `GET /runs/{id}/artifacts/...`.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse

from ..core import store
from ..core.catalog import CATALOG, get_entry
from ..core.datasets import BadArchive, UploadTooLarge, extract_dataset, save_upload
from ..core.models import RunRequest, RunState, RunStatus
from ..core.orchestrator import Orchestrator
from ..core.workspace import Workspace

router = APIRouter()


def _safe_name(filename: str) -> str:
    """Basename only, so an upload can't write outside the session dir."""
    return os.path.basename(filename).replace("\\", "_") or "upload.bin"


@router.get("/studies")
def list_studies():
    """The catalog: metadata + links only. No datasets are hosted here."""
    return list(CATALOG.values())


@router.get("/studies/{study_id}")
def get_study(study_id: str):
    try:
        return get_entry(study_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


def _execute(req: RunRequest, run_id: str) -> None:
    orch = Orchestrator(req, run_id)
    store.put(orch.state)          # register early so polling sees "running"
    orch.state.status = RunStatus.RUNNING
    result = orch.run()
    store.put(result)


@router.post("/runs", response_model=RunState)
def start_run(
    background: BackgroundTasks,
    study_id: str = Form(...),
    tc_confirmed: bool = Form(False),
    primary_endpoint: str | None = Form(None),
    new_study_plan: str | None = Form(None),
    dataset: UploadFile | None = File(None),
    dictionary: UploadFile | None = File(None),
):
    """Single entry point the frontend calls (multipart/form-data). The user attaches the
    dataset (+ data dictionary) they downloaded from CIBMTR under CIBMTR's Terms & Conditions;
    the files are saved ONLY to the run's ephemeral session dir and deleted when the run ends.
    Requires T&C confirmation. Runs in the background; poll GET /runs/{id}."""
    if study_id not in CATALOG and not new_study_plan:
        raise HTTPException(404, f"study '{study_id}' not in catalog")
    if not tc_confirmed:
        raise HTTPException(
            400,
            "CIBMTR Terms & Conditions must be confirmed before a session can use data.",
        )

    run_id = store.new_run_id()
    ws = Workspace(run_id)
    dataset_path: str | None = None
    dictionary_path: str | None = None
    try:
        if dataset is not None and dataset.filename:
            dst = ws.session_dir / _safe_name(dataset.filename)
            save_upload(dataset.file, dst)
            dataset_path = str(dst)
            extract_dataset(dst, ws.session_dir / "data")   # unzip for the agents' R
        if dictionary is not None and dictionary.filename:
            ddst = ws.session_dir / _safe_name(dictionary.filename)
            save_upload(dictionary.file, ddst)
            dictionary_path = str(ddst)
    except UploadTooLarge as exc:
        raise HTTPException(413, str(exc)) from exc
    except BadArchive as exc:
        raise HTTPException(400, f"dataset archive rejected: {exc}") from exc

    req = RunRequest(
        study_id=study_id, tc_confirmed=tc_confirmed, primary_endpoint=primary_endpoint,
        new_study_plan=new_study_plan, dataset_path=dataset_path,
        dictionary_path=dictionary_path,
    )
    state = RunState(run_id=run_id, study_id=study_id, status=RunStatus.QUEUED)
    store.put(state)
    background.add_task(_execute, req, run_id)
    return state


@router.get("/runs/{run_id}", response_model=RunState)
def get_run(run_id: str):
    state = store.get(run_id)
    if not state:
        raise HTTPException(404, "run not found")
    return state


@router.get("/runs/{run_id}/artifacts/{name:path}", response_class=PlainTextResponse)
def get_artifact(run_id: str, name: str):
    if not store.get(run_id):
        raise HTTPException(404, "run not found")
    # Only serve persisted artifacts, never anything under the ephemeral _session dir.
    if name.startswith("_session") or ".." in name:
        raise HTTPException(403, "forbidden path")
    path = Workspace(run_id).run_dir / name
    if not path.exists() or not path.is_file():
        raise HTTPException(404, f"artifact '{name}' not found")
    return path.read_text()
