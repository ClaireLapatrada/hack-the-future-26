"""
Shared data loaders for tool modules.

These three helpers are used by risk_tools, planning_tools, and operational_impact_tools.
Keeping them here avoids copy-pasting the same env-var resolution logic across files.

Env overrides:
  ERP_JSON_PATH               — path to ERP snapshot JSON (default: data/mock_erp.json)
  MANUFACTURER_PROFILE_PATH   — path to manufacturer profile JSON (default: config/manufacturer_profile.json)
"""

import json
import os
import warnings
from pathlib import Path

from backend.tools.guardrails import StaleDataWarning, check_data_freshness

_ROOT = Path(__file__).resolve().parent.parent
_DATA_DIR = _ROOT / "data"
_CONFIG_DIR = _ROOT / "config"

_STALE_DATA_MAX_AGE_HOURS = float(os.getenv("STALE_DATA_MAX_AGE_HOURS", "48"))


def _load_erp() -> dict:
    """Load ERP snapshot. Checks ERP_JSON_PATH env var first, then falls back to data/mock_erp.json."""
    env_path = os.getenv("ERP_JSON_PATH")
    path = Path(env_path) if env_path else _DATA_DIR / "mock_erp.json"
    if not check_data_freshness(path, max_age_hours=_STALE_DATA_MAX_AGE_HOURS):
        msg = (
            f"ERP data at '{path}' is stale (older than {_STALE_DATA_MAX_AGE_HOURS}h) "
            "or missing. Financial calculations may be based on outdated information."
        )
        warnings.warn(msg, StaleDataWarning, stacklevel=2)
        try:
            from backend.tools.audit_log import append_audit
            append_audit({
                "agent_id": "data_loader",
                "tool_name": "_load_erp",
                "arguments": {"path": str(path)},
                "outcome": "blocked",
                "error_message": msg,
                "duration_ms": 0.0,
            })
        except Exception:
            pass
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_profile() -> dict:
    """Load manufacturer profile. Checks MANUFACTURER_PROFILE_PATH env var first, then config/manufacturer_profile.json."""
    env_path = os.getenv("MANUFACTURER_PROFILE_PATH")
    path = Path(env_path) if env_path else _CONFIG_DIR / "manufacturer_profile.json"
    if not check_data_freshness(path, max_age_hours=_STALE_DATA_MAX_AGE_HOURS):
        msg = (
            f"Manufacturer profile at '{path}' is stale (older than {_STALE_DATA_MAX_AGE_HOURS}h) "
            "or missing. Risk/planning calculations may be based on outdated information."
        )
        warnings.warn(msg, StaleDataWarning, stacklevel=2)
        try:
            from backend.tools.audit_log import append_audit
            append_audit({
                "agent_id": "data_loader",
                "tool_name": "_load_profile",
                "arguments": {"path": str(path)},
                "outcome": "blocked",
                "error_message": msg,
                "duration_ms": 0.0,
            })
        except Exception:
            pass
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_active_disruption() -> dict:
    """Load active disruption config. Returns default inactive state if file is missing or unreadable."""
    for p in [_CONFIG_DIR / "active_disruption.json", _ROOT / "config" / "active_disruption.json"]:
        if p.exists():
            try:
                with open(p, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
    return {"active": False, "shipping_lanes": {}}
