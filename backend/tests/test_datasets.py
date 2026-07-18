"""Tests for the dataset upload/extract/parse helpers and the multipart /runs endpoint."""
import io
import zipfile
from pathlib import Path

import pytest
from openpyxl import Workbook


def test_save_upload_enforces_size_cap(tmp_path):
    from app.core.datasets import UploadTooLarge, save_upload
    big = io.BytesIO(b"x" * 2048)
    with pytest.raises(UploadTooLarge):
        save_upload(big, tmp_path / "f.bin", max_bytes=1024)
    assert not (tmp_path / "f.bin").exists()  # partial file cleaned up


def test_extract_dataset_roundtrip(tmp_path):
    from app.core.datasets import extract_dataset
    z = tmp_path / "d.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("data.csv", "a,b\n1,2\n")
        zf.writestr("sub/notes.txt", "hello")
    out = tmp_path / "out"
    names = extract_dataset(z, out)
    assert set(names) == {"data.csv", "sub/notes.txt"}
    assert (out / "data.csv").read_text().startswith("a,b")


def test_extract_dataset_blocks_path_traversal(tmp_path):
    from app.core.datasets import BadArchive, extract_dataset
    z = tmp_path / "evil.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("../escape.txt", "pwned")
    with pytest.raises(BadArchive):
        extract_dataset(z, tmp_path / "out")


def test_extract_dataset_ignores_non_zip(tmp_path):
    from app.core.datasets import extract_dataset
    f = tmp_path / "bare.csv"
    f.write_text("a,b\n1,2\n")
    assert extract_dataset(f, tmp_path / "out") == []


def test_dictionary_to_text_xlsx(tmp_path):
    from app.core.datasets import dictionary_to_text
    wb = Workbook()
    ws = wb.active
    ws.append(["variable", "description"])
    ws.append(["age_grp", "age category at transplant"])
    p = tmp_path / "dict.xlsx"
    wb.save(p)
    text = dictionary_to_text(p)
    assert "age_grp" in text and "age category at transplant" in text


def test_dictionary_to_text_rtf(tmp_path):
    from app.core.datasets import dictionary_to_text
    p = tmp_path / "dict.rtf"
    p.write_text(r"{\rtf1\ansi age_grp = age category\par kps = performance status}")
    text = dictionary_to_text(p)
    assert "age_grp" in text and "performance status" in text


def test_runs_endpoint_multipart(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("RUNS_DIR", str(tmp_path / "runs"))
    from app.core.config import get_settings
    get_settings.cache_clear()
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)

    zbytes = io.BytesIO()
    with zipfile.ZipFile(zbytes, "w") as zf:
        zf.writestr("cohort.csv", "id,age\n1,72\n")
    zbytes.seek(0)

    # Missing T&C -> 400
    r = c.post("/runs", data={"study_id": "P-5297", "tc_confirmed": "false"})
    assert r.status_code == 400

    # Valid multipart with a dataset zip -> 200 + a run id (run then errors in bg w/o API key)
    r = c.post(
        "/runs",
        data={"study_id": "P-5297", "tc_confirmed": "true", "primary_endpoint": "OS"},
        files={"dataset": ("P-5297.zip", zbytes.getvalue(), "application/zip")},
    )
    assert r.status_code == 200
    assert r.json()["run_id"]
    get_settings.cache_clear()
