"""
GET  /api/rules   — return current rules config
POST /api/rules   — merge-update initialValues and persist

Mirrors ui/app/api/rules/route.ts.
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel

from backend.data import DataStore, get_data_store
from backend.models.rules import RulesConfig

router = APIRouter()


class UpdateRulesBody(BaseModel):
    initialValues: Dict[str, Any]


@router.get("/api/rules", response_model=Dict[str, Any])
def get_rules(store: DataStore = Depends(get_data_store)) -> Dict[str, Any]:
    """Return the full rules config."""
    try:
        return store.load_rules().model_dump()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to load rules config") from exc


@router.post("/api/rules", response_model=Dict[str, Any])
def update_rules(
    body: UpdateRulesBody = Body(...),
    store: DataStore = Depends(get_data_store),
) -> Dict[str, Any]:
    """
    Merge-update initialValues.

    Only keys defined in the RulesConfig sections schema are accepted (G6 allowlist).
    Unknown keys are rejected with 422.  Value types are also validated against the
    RuleDef schema (slider → numeric in range, toggle → boolean, input → string).
    """
    if not body.initialValues:
        raise HTTPException(status_code=400, detail="Missing or invalid initialValues")

    config = store.load_rules()

    # G6: Build allowlist from all RuleDef keys across all sections
    allowed_keys: Dict[str, Any] = {}  # key → RuleDef
    for section in config.sections:
        for rule_def in section.rules:
            allowed_keys[rule_def.key] = rule_def

    unknown_keys = [k for k in body.initialValues if k not in allowed_keys]
    if unknown_keys:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Unknown rule keys rejected (not in schema allowlist)",
                "unknown_keys": unknown_keys,
                "allowed_keys": list(allowed_keys.keys()),
            },
        )

    # G6: Type-validate submitted values against their RuleDef schema
    type_errors: list[str] = []
    for key, value in body.initialValues.items():
        rule_def = allowed_keys[key]
        if rule_def.type == "slider":
            if not isinstance(value, (int, float)):
                type_errors.append(f"'{key}': expected numeric (slider), got {type(value).__name__}")
            elif not (rule_def.min <= float(value) <= rule_def.max):
                type_errors.append(
                    f"'{key}'={value} out of range [{rule_def.min}, {rule_def.max}]"
                )
        elif rule_def.type == "toggle":
            if not isinstance(value, bool):
                type_errors.append(f"'{key}': expected boolean (toggle), got {type(value).__name__}")
        elif rule_def.type == "input":
            if not isinstance(value, str):
                type_errors.append(f"'{key}': expected string (input), got {type(value).__name__}")
            elif len(value) > 500:
                type_errors.append(f"'{key}': string exceeds 500 character limit")

    if type_errors:
        raise HTTPException(
            status_code=422,
            detail={"error": "Rule value type validation failed", "type_errors": type_errors},
        )

    merged = {**config.initialValues, **body.initialValues}
    updated = RulesConfig(sections=config.sections, initialValues=merged)
    store.save_rules(updated)
    return updated.model_dump()
