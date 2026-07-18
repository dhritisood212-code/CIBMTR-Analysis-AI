"""Contract validation: each agent's typed output is validated against its JSON Schema
before the next agent runs. A malformed artifact halts the run with a ContractError instead
of silently corrupting downstream steps.

Markdown artifacts (match-report.md, derivation-check.md, diagnosis.md) carry a required YAML
front-matter block; we validate that block's shape here and leave the prose free.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

from .config import get_settings


class ContractError(ValueError):
    """An agent produced output that violates its file contract."""


def _load_schema(name: str) -> dict:
    path = get_settings().schemas_dir / name
    return json.loads(path.read_text())


# Map artifact filename -> (parser, schema file). None schema = structural-only checks.
_YAML_SCHEMAS = {
    "study-spec.yaml": "study-spec.schema.json",
    "target-results.yaml": "target-results.schema.json",
    "agent-results.yaml": "agent-results.schema.json",
}


def validate_yaml_artifact(name: str, text: str) -> dict:
    """Parse and validate a YAML artifact. Returns the parsed object."""
    try:
        obj = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ContractError(f"{name}: not valid YAML - {exc}") from exc
    if name in _YAML_SCHEMAS:
        schema = _load_schema(_YAML_SCHEMAS[name])
        # Resolve local $ref to reproducibility-class.schema.json.
        validator = Draft202012Validator(
            schema, registry=_registry_with_shared_enums()
        )
        errors = sorted(validator.iter_errors(obj), key=lambda e: e.path)
        if errors:
            top = best_match(errors)
            raise ContractError(
                f"{name}: fails schema {_YAML_SCHEMAS[name]} at "
                f"{list(top.absolute_path)}: {top.message}"
            )
    return obj


def _registry_with_shared_enums():
    """Build a referencing registry so $ref: reproducibility-class.schema.json resolves."""
    from referencing import Registry, Resource

    shared = _load_schema("reproducibility-class.schema.json")
    resource = Resource.from_contents(shared)
    return Registry().with_resource(
        uri="reproducibility-class.schema.json", resource=resource
    )


def validate_markdown_frontmatter(name: str, text: str, required_keys: list[str]) -> dict:
    """Extract and shape-check the YAML front matter of a Markdown artifact."""
    if not text.lstrip().startswith("---"):
        raise ContractError(f"{name}: missing required YAML front matter block.")
    _, fm, _ = text.split("---", 2)
    try:
        meta = yaml.safe_load(fm) or {}
    except yaml.YAMLError as exc:
        raise ContractError(f"{name}: front matter is not valid YAML - {exc}") from exc
    missing = [k for k in required_keys if k not in meta]
    if missing:
        raise ContractError(f"{name}: front matter missing keys {missing}.")
    return meta


def assert_classes_frozen(target_results: dict, prior: dict | None) -> None:
    """Anti-tuning guard: the reproducibility classes in target-results.yaml must not change
    within a run. Called if the Interpreter is ever re-invoked mid-loop (it should not be)."""
    if prior is None:
        return
    def classes(tr: dict) -> dict[str, str]:
        out = {}
        for t in tr.get("targets", []) + tr.get("table1_targets", []):
            out[t["id"]] = t["reproducibility_class"]
        return out
    before, after = classes(prior), classes(target_results)
    changed = {k: (before[k], after[k]) for k in before if k in after and before[k] != after[k]}
    if changed:
        raise ContractError(
            "Reproducibility classes changed within a run (anti-tuning violation): "
            f"{changed}. Classes are frozen once assigned; a genuine reclassification "
            "requires a fresh run, not a mid-loop edit."
        )


def validate_no_fabricated_numbers(agent_results: dict, target_results: dict) -> list[str]:
    """Every observed value must cite an R source, and every target id must be accounted for.
    Returns a list of warnings (empty = clean)."""
    warnings: list[str] = []
    target_ids = {t["id"] for t in
                  target_results.get("targets", []) + target_results.get("table1_targets", [])}
    seen = set()
    for r in agent_results.get("results", []):
        seen.add(r["target_id"])
        obs = r.get("observed") or {}
        has_value = obs.get("point") is not None
        if has_value and not r.get("source"):
            warnings.append(
                f"target '{r['target_id']}' has an observed value but no R source - "
                "possible fabrication; rejecting."
            )
        if not has_value and not r.get("not_computed_reason"):
            warnings.append(
                f"target '{r['target_id']}' has no value and no not_computed_reason."
            )
    for missing in target_ids - seen:
        warnings.append(f"target '{missing}' was never scored by the Analyst.")
    return warnings
