"""The Orchestrator: sequences the six agents over a per-run working directory and exposes a
single entry point (used by both the API and the CLI).

Key design decisions encoded here:

  * **Numbers only come from executed R.** The Cohort and Analyst agents emit *R scripts*; the
    orchestrator runs them in the sandbox, and the scripts themselves write the data artifacts
    (analytic.parquet, table1.md) and - crucially - `agent-results.yaml` directly from
    computed R objects. The model never types a computed statistic into a results file. This
    is the fabrication firewall, enforced structurally rather than by trust.

  * **Anti-tuning ordering.** The Interpreter writes `target-results.yaml` (with frozen
    classes) FIRST; the Comparator scores against those classes; the Diagnoser may only
    propose paper/dictionary-grounded fixes. The orchestrator never lets the loop edit
    `target-results.yaml`.

  * **Fails clearly when unconfigured.** Missing API key or R sandbox -> the run stops in
    RunStatus.ERROR with an actionable message, not a crash or a silent partial.
"""
from __future__ import annotations

from pathlib import Path

from ..agents.registry import system_prompt
from . import contracts
from .anthropic_client import (
    AgentCall,
    AnthropicCallError,
    AnthropicNotConfigured,
    run_agent,
)
from .config import get_settings
from .models import RunRequest, RunState, RunStatus, Stage
from .r_runner import RExecutionError, RSandboxNotConfigured, run_r_script
from .workspace import Workspace

# Sanity bound on how much untrusted file text we hand the model as DATA (not instructions).
_MAX_DATA_CHARS = 60_000


class Orchestrator:
    def __init__(self, req: RunRequest, run_id: str):
        self.req = req
        self.state = RunState(run_id=run_id, study_id=req.study_id)
        self.ws = Workspace(run_id)
        self.settings = get_settings()
        self._target_results: dict | None = None

    # ---- public entry point ----
    def run(self) -> RunState:
        try:
            self._guard_compliance()
            self._interpret()
            self._cohort()
            self._analyze()
            self._compare()
            self._diagnose_loop()
            self._finalize()
        except (AnthropicNotConfigured, RSandboxNotConfigured) as exc:
            self._error(f"Not configured: {exc}")
        except (AnthropicCallError, RExecutionError, contracts.ContractError) as exc:
            self._error(str(exc))
        finally:
            self.ws.purge_session()   # never persist the user's source data
        return self.state

    # ---- stages ----
    def _guard_compliance(self) -> None:
        if not self.req.tc_confirmed:
            raise contracts.ContractError(
                "CIBMTR Terms & Conditions not confirmed for this session. The app stores only "
                "study metadata/links; the user must download the dataset from CIBMTR and "
                "accept its T&C before a session can use data."
            )
        if not self.req.dataset_path and not self.req.new_study_plan:
            raise contracts.ContractError(
                "No dataset was attached for this session. Download the study's dataset (and "
                "data dictionary) from CIBMTR under its Terms & Conditions, then attach them "
                "when starting the run. The app never fetches or stores the data itself."
            )

    def _interpret(self) -> None:
        self.state.record(Stage.INTERPRET, "started")
        data = self._dictionary_blocks()
        payload_spec = (
            f"STUDY_ID: {self.req.study_id}\n"
            "TASK: Produce `study-spec.yaml` conforming to study-spec.schema.json. Read the "
            "methods (and, for P-5297, apply the hardcoded ground truth in your prompt). "
            "Return ONLY the YAML."
        )
        spec_text = self._call("study_interpreter", payload_spec, data)
        contracts.validate_yaml_artifact("study-spec.yaml", spec_text)
        self.ws.write_artifact("study-spec.yaml", spec_text)
        self.state.record(Stage.INTERPRET, "completed", artifact="study-spec.yaml")

        payload_targets = (
            f"STUDY_ID: {self.req.study_id}\n"
            "TASK: Produce `target-results.yaml` conforming to target-results.schema.json. "
            "Assign each target a reproducibility class NOW, before any analysis, each with a "
            "class_reason grounded in the methods + dictionary. Fill expected values only from "
            "figures you actually read; leave unknown ones null with a TODO note. Return ONLY "
            "the YAML.\n\n"
            "For context, here is the study-spec you just produced:\n" + spec_text
        )
        targets_text = self._call("study_interpreter", payload_targets, data)
        self._target_results = contracts.validate_yaml_artifact(
            "target-results.yaml", targets_text
        )
        self.ws.write_artifact("target-results.yaml", targets_text)
        self.state.record(Stage.INTERPRET, "completed", artifact="target-results.yaml")

    def _cohort(self) -> None:
        """Build (2a) and/or assemble (2b) the analytic cohort. Both emit R that the sandbox
        runs to produce the SHARED-SCHEMA analytic.parquet + sidecar."""
        spec = self.ws.read_artifact("study-spec.yaml")
        data = self._dictionary_blocks()

        # 2a Cohort Builder: derive from raw + self-check (validated part of the Builder).
        self.state.record(Stage.BUILD_COHORT, "started")
        builder_payload = (
            "TASK: Emit an R script `build_cohort.R` that derives endpoints/covariates from "
            "raw component fields, writes analytic.parquet + analytic.schema.yaml (shared "
            "contract), and writes derivation-check.md checking your derivations against the "
            "file's own pre-computed columns. Read data via the session dataset path provided "
            "at runtime. Return ONLY the R.\n\n"
            f"study-spec.yaml:\n{spec}"
        )
        build_r = self._call("cohort_builder", builder_payload, data)
        self._run_r("build_cohort.R", build_r, Stage.BUILD_COHORT)
        self.state.record(Stage.BUILD_COHORT, "completed", artifact="derivation-check.md")

        # 2b Cohort Assembler: final filters + Table 1 + attrition, same analytic.parquet schema.
        self.state.record(Stage.ASSEMBLE_COHORT, "started")
        assembler_payload = (
            "TASK: Emit an R script `assemble_cohort.R` that applies the study's final analytic "
            "filters, writes analytic.parquet + analytic.schema.yaml (identical schema to the "
            "Builder's), table1.md, and attrition.md. Preserve factor levels/reference from the "
            "spec. Return ONLY the R.\n\n"
            f"study-spec.yaml:\n{spec}"
        )
        assemble_r = self._call("cohort_assembler", assembler_payload, data)
        self._run_r("assemble_cohort.R", assemble_r, Stage.ASSEMBLE_COHORT)
        for art in ("table1.md", "attrition.md"):
            if self.ws.has(art):
                self.state.record(Stage.ASSEMBLE_COHORT, "completed", artifact=art)

    def _analyze(self) -> None:
        self.state.record(Stage.ANALYZE, "started")
        spec = self.ws.read_artifact("study-spec.yaml")
        targets = self.ws.read_artifact("target-results.yaml")
        script_name = f"reproduce_{self.req.study_id}.R"
        payload = (
            f"TASK: Emit the artifact script `{script_name}`. It must be clean, sectioned, "
            "commented (each modeling choice referencing the paper's methods), deterministic "
            "(set.seed), self-contained, and it must WRITE its results to results/*.csv|png AND "
            "write `agent-results.yaml` (agent-results.schema.json) directly from the computed "
            "R objects - never hand-typed. Also write sessionInfo.txt. Choose estimators by the "
            "estimand in the spec; call the cibmtrrepro package's canonical functions. Do NOT "
            "tune toward the target values. Return ONLY the R.\n\n"
            f"study-spec.yaml:\n{spec}\n\n"
            f"target-results.yaml (for WHICH quantities to compute - not to tune toward):\n{targets}"
        )
        if self.req.primary_endpoint:
            payload += f"\n\nSCOPE: start with primary endpoint '{self.req.primary_endpoint}'."
        analysis_r = self._call("analyst", payload)
        self.ws.write_artifact(script_name, analysis_r)
        result = self._run_r(script_name, analysis_r, Stage.ANALYZE, already_written=True)

        # Fabrication firewall: agent-results.yaml must exist, validate, and cite R sources.
        if not self.ws.has("agent-results.yaml"):
            raise contracts.ContractError(
                f"{script_name} ran (exit {result.exit_code}) but did not write "
                "agent-results.yaml. The Analyst's script must emit results from computed R."
            )
        agent_results = contracts.validate_yaml_artifact(
            "agent-results.yaml", self.ws.read_artifact("agent-results.yaml")
        )
        warnings = contracts.validate_no_fabricated_numbers(
            agent_results, self._target_results or {}
        )
        if warnings:
            raise contracts.ContractError(
                "Fabrication / coverage check failed:\n- " + "\n- ".join(warnings)
            )
        self.state.record(Stage.ANALYZE, "completed", artifact=script_name)
        self.state.record(Stage.ANALYZE, "completed", artifact="agent-results.yaml")

    def _compare(self) -> None:
        self.state.record(Stage.COMPARE, "started")
        payload = (
            "TASK: Produce `match-report.md` (match-report.contract.md). Check Table 1 FIRST. "
            "Score each target against its PRE-ASSIGNED class from target-results.yaml - do not "
            "recompute classes. Return ONLY the Markdown (with the required YAML front matter).\n\n"
            f"target-results.yaml:\n{self.ws.read_artifact('target-results.yaml')}\n\n"
            f"agent-results.yaml:\n{self.ws.read_artifact('agent-results.yaml')}\n\n"
            f"table1.md:\n{self._safe_read('table1.md')}\n\n"
            f"attrition.md:\n{self._safe_read('attrition.md')}\n\n"
            f"Tolerances: {self._tolerance_summary()}"
        )
        report = self._call("comparator", payload)
        meta = contracts.validate_markdown_frontmatter(
            "match-report.md", report,
            required_keys=["study_id", "run_id", "verdict", "table1_reconciled", "summary"],
        )
        self.ws.write_artifact("match-report.md", report)
        self.state.verdict = meta.get("verdict")
        self.state.record(Stage.COMPARE, "completed", detail=f"verdict={self.state.verdict}",
                          artifact="match-report.md")

    def _diagnose_loop(self) -> None:
        verdict = (self.state.verdict or "").lower()
        should_iterate = verdict == "fail" or (
            verdict == "partial" and self.settings.iterate_on_partial
        )
        while should_iterate and self.state.iteration < self.settings.max_diagnose_iterations:
            self.state.iteration += 1
            self.state.record(Stage.DIAGNOSE, "started",
                              detail=f"iteration {self.state.iteration}")
            payload = (
                "TASK: Produce `diagnosis.md` (diagnosis.contract.md). Localize each unexplained "
                "mismatch to method-spec | cohort-builder | cohort-assembler. Every fix MUST be "
                "grounded in the paper or dictionary; run the forbidden-reason check on yourself "
                "and refuse fixes justified only by closeness to the target. Return ONLY the "
                "Markdown.\n\n"
                f"match-report.md:\n{self.ws.read_artifact('match-report.md')}\n\n"
                f"study-spec.yaml:\n{self.ws.read_artifact('study-spec.yaml')}\n\n"
                f"attrition.md:\n{self._safe_read('attrition.md')}"
            )
            diagnosis = self._call("diagnoser", payload)
            contracts.validate_markdown_frontmatter(
                "diagnosis.md", diagnosis, required_keys=["run_id", "diagnoses"]
            )
            self.ws.write_artifact(f"diagnosis_{self.state.iteration}.md", diagnosis)
            self.state.record(Stage.DIAGNOSE, "completed",
                              artifact=f"diagnosis_{self.state.iteration}.md")

            # Applying a fix = re-running the localized agent with the correction in context,
            # then re-analyzing and re-comparing. target-results.yaml is NEVER edited.
            # (Re-run wiring is deliberately conservative; see docs/TODO.md - the loop applies
            #  fixes by re-invoking _cohort()/_analyze() with the diagnosis appended. Kept
            #  single-pass here to avoid unbounded model spend without an operator in the loop.)
            self._reanalyze_with_fix(diagnosis)
            verdict = (self.state.verdict or "").lower()
            should_iterate = verdict == "fail" or (
                verdict == "partial" and self.settings.iterate_on_partial
            )

    def _reanalyze_with_fix(self, diagnosis: str) -> None:
        """Re-run Analyst + Comparator with the diagnosis in context. Cohort-level fixes would
        additionally re-run _cohort(); gated behind an operator flag in production (see TODO)."""
        spec = self.ws.read_artifact("study-spec.yaml")
        targets = self.ws.read_artifact("target-results.yaml")
        script_name = f"reproduce_{self.req.study_id}.R"
        payload = (
            f"TASK: Revise `{script_name}` applying ONLY the paper/dictionary-grounded fixes in "
            "the diagnosis below. Do not tune toward targets. Return ONLY the R.\n\n"
            f"DIAGNOSIS:\n{diagnosis}\n\nstudy-spec.yaml:\n{spec}\n\n"
            f"target-results.yaml:\n{targets}"
        )
        revised = self._call("analyst", payload)
        self.ws.write_artifact(script_name, revised)
        self._run_r(script_name, revised, Stage.ANALYZE, already_written=True)
        self._compare()

    def _finalize(self) -> None:
        verdict = (self.state.verdict or "").lower()
        self.state.status = {
            "pass": RunStatus.PASSED,
            "partial": RunStatus.PARTIAL,
            "fail": RunStatus.FAILED,
        }.get(verdict, RunStatus.FAILED)
        self.state.record(Stage.DONE, "completed", detail=f"final verdict={verdict}")
        self.ws.commit(f"run {self.state.run_id}: {self.req.study_id} -> {verdict}")

    # ---- helpers ----
    def _call(self, agent_key: str, payload: str, data_blocks=None) -> str:
        text = run_agent(AgentCall(
            agent_key=agent_key,
            system_prompt=system_prompt(agent_key),
            user_payload=payload,
            data_blocks=data_blocks,
        ))
        return _strip_code_fence(text)

    def _run_r(self, name: str, script: str, stage: Stage, already_written: bool = False):
        if not already_written:
            self.ws.write_artifact(name, script)
        script_path = self.ws.run_dir / name
        result = run_r_script(script_path, self.ws.run_dir)
        if result.session_info:
            self.ws.write_artifact("sessionInfo.txt", result.session_info)
        if result.exit_code != 0:
            raise RExecutionError(
                f"{name} exited {result.exit_code} in the R sandbox.\nstderr:\n{result.stderr[-4000:]}"
            )
        self.state.record(stage, "completed", detail=f"{name} ran in {result.wall_seconds:.1f}s")
        return result

    def _dictionary_blocks(self) -> list[tuple[str, str]]:
        from .datasets import dictionary_to_text
        blocks: list[tuple[str, str]] = []
        if self.req.dictionary_path:
            blocks.append(("DATA DICTIONARY (untrusted file content)",
                           dictionary_to_text(Path(self.req.dictionary_path))))
        listing = self._data_file_listing()
        if listing:
            blocks.append(("DATASET FILES (untrusted; the analytic files your R must read)",
                           listing))
        return blocks

    def _data_file_listing(self) -> str:
        """Where the unzipped dataset lives, relative to the R working directory, plus a file
        listing so the cohort agents' R reads the right files. Data stays in the ephemeral,
        gitignored, purged _session dir."""
        data_dir = self.ws.session_dir / "data"
        if data_dir.exists():
            rel = data_dir.relative_to(self.ws.run_dir)  # e.g. _session/data
            lines = [f"The analytic data files are in ./{rel}/ (relative to the R working "
                     f"directory). Read them from there. Files:"]
            for f in sorted(data_dir.rglob("*")):
                if f.is_file():
                    lines.append(f"  {f.relative_to(data_dir)}\t{f.stat().st_size} bytes")
            return "\n".join(lines)
        if self.req.dataset_path:   # a bare (non-zip) file was uploaded
            p = Path(self.req.dataset_path)
            rel = p.relative_to(self.ws.run_dir)
            return (f"The analytic data file is ./{rel} (relative to the R working directory), "
                    f"{p.stat().st_size} bytes.")
        return ""

    def _safe_read(self, name: str) -> str:
        return self.ws.read_artifact(name) if self.ws.has(name) else "(not produced)"

    def _tolerance_summary(self) -> str:
        from .config import get_tolerances
        t = get_tolerances()
        return (f"cohort_n +-{t.cohort_n_rel:.0%}, table1 +-{t.table1_prop_pts*100:.0f}pts, "
                f"median +-{t.median_months}mo, CIF/KM +-{t.cif_km_abs} abs, "
                f"HR +-{t.hr_rel:.0%} rel + same direction + same significance")

    def _error(self, msg: str) -> None:
        self.state.status = RunStatus.ERROR
        self.state.error = msg
        self.state.record(self.state.stage, "error", detail=msg)


def _strip_code_fence(text: str) -> str:
    """Models sometimes wrap a single artifact in a ```lang fence; unwrap it if so."""
    s = text.strip()
    if s.startswith("```"):
        lines = s.splitlines()
        if lines[-1].strip().startswith("```"):
            return "\n".join(lines[1:-1]).strip() + "\n"
    return text


def _read_text_capped(path: Path) -> str:
    raw = path.read_text(errors="replace")
    return raw if len(raw) <= _MAX_DATA_CHARS else raw[:_MAX_DATA_CHARS] + "\n...[truncated]..."
