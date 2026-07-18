"""Loads the six agent prompts from agents/*.md and prepends the shared preamble.

Prompts are plain Markdown files (diffable, reviewable in PRs) - the durable definition of
each agent lives in agents/, not in Python string literals.
"""
from __future__ import annotations

from functools import lru_cache

from ..core.config import get_settings

# agent_key -> prompt filename in agents/
AGENT_FILES = {
    "study_interpreter": "study_interpreter.md",
    "cohort_builder": "cohort_builder.md",
    "cohort_assembler": "cohort_assembler.md",
    "analyst": "analyst.md",
    "comparator": "comparator.md",
    "diagnoser": "diagnoser.md",
}


@lru_cache
def _preamble() -> str:
    return (get_settings().agents_dir / "_shared_preamble.md").read_text()


@lru_cache
def system_prompt(agent_key: str) -> str:
    if agent_key not in AGENT_FILES:
        raise KeyError(f"unknown agent '{agent_key}'")
    scoped = (get_settings().agents_dir / AGENT_FILES[agent_key]).read_text()
    return f"{_preamble()}\n\n---\n\n{scoped}"
