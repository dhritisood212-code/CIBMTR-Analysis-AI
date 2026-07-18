"""FastAPI app. `uvicorn app.main:app --reload`."""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .core.anthropic_client import require_client
from .core.config import get_settings
from .core.r_runner import require_sandbox, run_r_script

app = FastAPI(
    title="CIBMTR Reproduction Panel",
    version="0.1.0",
    description=(
        "A research/educational secondary-analysis tool. Not medical advice, not a clinical "
        "or regulatory instrument. Reproduces published CIBMTR studies from public datasets; "
        "outputs are drafts for expert review. CIBMTR did not review or endorse any analysis."
    ),
)

# Allow the hosted static frontend (Netlify) to call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/health")
def health():
    """Reports config readiness WITHOUT failing - the app runs unconfigured; runs fail clearly."""
    settings = get_settings()
    try:
        require_client()
        anthropic_ready = True
        anthropic_msg = "configured"
    except Exception as exc:  # noqa: BLE001
        anthropic_ready = False
        anthropic_msg = str(exc).splitlines()[0]
    return {
        "status": "ok",
        "anthropic_ready": anthropic_ready,
        "anthropic": anthropic_msg,
        "runs_dir": str(settings.runs_dir),
        "models": {
            "interpreter": settings.interpreter_model,
            "analyst": settings.analyst_model,
            "comparator": settings.comparator_model,
        },
        "disclaimer": (
            "Research/educational tool. Not medical advice. CIBMTR did not review or endorse "
            "any analysis produced here."
        ),
    }


# A tiny R script that loads the internal package and runs a real KM fit on trivial data.
# times 1..10 (all events) -> median survival = 5. If this prints, R + cibmtrrepro + the
# sandbox all work end to end.
_R_HEALTH_SCRIPT = """\
suppressPackageStartupMessages(library(cibmtrrepro))
d <- data.frame(time = 1:10, event = rep(1L, 10))
m <- km_fit(d, "time", "event")
cat(sprintf("R_OK median=%s\\n", m$medians$median[[1]]))
writeLines("ok", "r_health.txt")
"""


@app.get("/r-health")
def r_health():
    """Runs a real R script through the sandbox to verify the R runtime works in this
    deployment. Returns cleanly (does not raise) so it's safe to poll from a browser."""
    try:
        require_sandbox()
    except Exception as exc:  # noqa: BLE001
        return {"r_ready": False, "stage": "sandbox", "detail": str(exc).splitlines()[0]}

    run_dir = Path(tempfile.mkdtemp(prefix="rhealth_"))
    try:
        script = run_dir / "r_health.R"
        script.write_text(_R_HEALTH_SCRIPT)
        result = run_r_script(script, run_dir)
        ok = result.exit_code == 0 and (run_dir / "r_health.txt").exists()
        return {
            "r_ready": ok,
            "exit_code": result.exit_code,
            "stdout": result.stdout.strip()[-500:],
            "stderr": result.stderr.strip()[-500:],
            "wall_seconds": round(result.wall_seconds, 2),
        }
    except Exception as exc:  # noqa: BLE001
        return {"r_ready": False, "stage": "execute", "detail": str(exc).splitlines()[0]}
    finally:
        import shutil
        shutil.rmtree(run_dir, ignore_errors=True)
