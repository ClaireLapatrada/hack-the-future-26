"""
Centralised settings for the backend.

All hardcoded Path(__file__).resolve().parent.parent chains in tool files
will be replaced by importing from here in later phases.
Environment variables map 1-to-1 with the names already used across tools
(ERP_JSON_PATH, MANUFACTURER_PROFILE_PATH, etc.) so existing .env files
continue to work without modification.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ dir — data, config, agents all live here now
_BACKEND_ROOT = Path(__file__).resolve().parent
# Repo root — used for .env loading and project_root field
_PROJECT_ROOT = _BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Repo layout ────────────────────────────────────────────────────────
    project_root: Path = _PROJECT_ROOT
    data_dir: Path = _BACKEND_ROOT / "data"
    config_dir: Path = _BACKEND_ROOT / "config"
    ui_data_dir: Path = _PROJECT_ROOT / "frontend" / "data"

    # ── Path overrides (honour existing env var names used in tools) ───────
    erp_json_path: Optional[Path] = Field(default=None, alias="ERP_JSON_PATH")
    manufacturer_profile_path: Optional[Path] = Field(
        default=None, alias="MANUFACTURER_PROFILE_PATH"
    )
    planning_config_path: Optional[Path] = Field(
        default=None, alias="PLANNING_CONFIG_PATH"
    )
    action_config_path: Optional[Path] = Field(
        default=None, alias="ACTION_CONFIG_PATH"
    )

    # ── Agent / model config ───────────────────────────────────────────────
    gemini_model: str = Field(
        default="gemini-2.5-flash-lite", alias="GEMINI_MODEL"
    )
    orchestrator_use_flat: bool = Field(
        default=False, alias="ORCHESTRATOR_USE_FLAT"
    )
    orchestrator_subagents: str = Field(
        default="all", alias="ORCHESTRATOR_SUBAGENTS"
    )
    subagent_breather_seconds: int = Field(
        default=10, alias="SUBAGENT_BREATHER_SECONDS"
    )
    tool_call_delay_seconds: float = Field(
        default=3.0, alias="TOOL_CALL_DELAY_SECONDS"
    )

    # ── External service credentials ───────────────────────────────────────
    google_search_api_key: Optional[str] = Field(
        default=None, alias="GOOGLE_SEARCH_API_KEY"
    )
    google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    google_search_engine_id: Optional[str] = Field(
        default=None, alias="GOOGLE_SEARCH_ENGINE_ID"
    )
    nasa_api_key: Optional[str] = Field(default=None, alias="NASA_API_KEY")
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    qdrant_url: Optional[str] = Field(default=None, alias="QDRANT_URL")
    qdrant_host: Optional[str] = Field(default=None, alias="QDRANT_HOST")

    # ── Derived path helpers ───────────────────────────────────────────────

    @property
    def effective_erp_path(self) -> Path:
        return self.erp_json_path or (self.data_dir / "mock_erp.json")

    @property
    def effective_profile_path(self) -> Path:
        return self.manufacturer_profile_path or (
            self.config_dir / "manufacturer_profile.json"
        )

    @property
    def effective_planning_config_path(self) -> Path:
        return self.planning_config_path or (_BACKEND_ROOT / "planning_config.json")

    @property
    def effective_action_config_path(self) -> Path:
        return self.action_config_path or (self.config_dir / "action_config.json")

    @property
    def active_disruption_path(self) -> Path:
        return self.config_dir / "active_disruption.json"

    @property
    def disruption_history_path(self) -> Path:
        """Primary disruption history path; falls back checked in DataStore."""
        return self.data_dir / "mock_disruption_history.json"

    @property
    def pending_approvals_path(self) -> Path:
        return self.data_dir / "pending_approvals.json"

    @property
    def escalations_path(self) -> Path:
        return self.data_dir / "escalations.json"

    @property
    def planning_documents_path(self) -> Path:
        return self.data_dir / "planning_documents.json"

    @property
    def agent_stream_path(self) -> Path:
        return self.data_dir / "agent_reasoning_stream.json"

    @property
    def approval_resolutions_path(self) -> Path:
        return self.data_dir / "approval_resolutions.json"

    @property
    def rules_path(self) -> Path:
        return self.config_dir / "rules.json"


# Module-level singleton — import this everywhere instead of re-instantiating.
settings = Settings()
