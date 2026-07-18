"""Configuration. Loaded from environment / .env (see backend/.env.example).

Nothing here raises on import when a value is missing - the app must be able to *start*
unconfigured. The clear, actionable errors happen at the point of use (see
anthropic_client.require_client() and r_runner.require_sandbox()).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Tolerances(BaseSettings):
    """Default reproduction tolerances from the brief. All configurable via env."""
    model_config = SettingsConfigDict(env_prefix="TOL_", env_file=".env", extra="ignore")

    cohort_n_rel: float = 0.05        # cohort n +-5%
    table1_prop_pts: float = 0.03     # Table 1 proportions +-3 pts
    median_months: float = 2.0        # median survival +-2 months
    cif_km_abs: float = 0.02          # CIF / KM point estimate +-0.02 absolute
    hr_rel: float = 0.10              # HR +-10% relative (AND same direction + significance)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Anthropic
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    max_tokens: int = Field(default=8192, alias="MAX_TOKENS")

    # Per-agent models. Configurable; check https://docs.claude.com for the current list.
    interpreter_model: str = Field(default="claude-opus-4-8", alias="INTERPRETER_MODEL")
    builder_model: str = Field(default="claude-sonnet-5", alias="BUILDER_MODEL")
    assembler_model: str = Field(default="claude-sonnet-5", alias="ASSEMBLER_MODEL")
    analyst_model: str = Field(default="claude-opus-4-8", alias="ANALYST_MODEL")
    comparator_model: str = Field(default="claude-sonnet-5", alias="COMPARATOR_MODEL")
    diagnoser_model: str = Field(default="claude-opus-4-8", alias="DIAGNOSER_MODEL")

    # R sandbox
    r_sandbox_cmd: str = Field(default="infra/run_r_sandboxed.sh", alias="R_SANDBOX_CMD")
    r_timeout_seconds: int = Field(default=300, alias="R_TIMEOUT_SECONDS")
    r_max_memory_mb: int = Field(default=4096, alias="R_MAX_MEMORY_MB")

    # Loop
    max_diagnose_iterations: int = Field(default=2, alias="MAX_DIAGNOSE_ITERATIONS")
    iterate_on_partial: bool = Field(default=False, alias="ITERATE_ON_PARTIAL")

    # Storage
    runs_dir: Path = Field(default=Path("./runs"), alias="RUNS_DIR")
    session_data_ttl_minutes: int = Field(default=120, alias="SESSION_DATA_TTL_MINUTES")

    # CORS: comma-separated allowed origins for the hosted frontend, e.g.
    # "https://cibmtr-repro.netlify.app". "*" allows any origin (fine for a public demo API
    # that hosts no secrets and no user data at rest).
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # Repo roots (resolved relative to this file so paths work regardless of cwd)
    repo_root: Path = Path(__file__).resolve().parents[3]

    @property
    def agents_dir(self) -> Path:
        return self.repo_root / "agents"

    @property
    def schemas_dir(self) -> Path:
        return self.repo_root / "schemas"

    def model_for(self, agent_key: str) -> str:
        return {
            "study_interpreter": self.interpreter_model,
            "cohort_builder": self.builder_model,
            "cohort_assembler": self.assembler_model,
            "analyst": self.analyst_model,
            "comparator": self.comparator_model,
            "diagnoser": self.diagnoser_model,
        }[agent_key]


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_tolerances() -> Tolerances:
    return Tolerances()
