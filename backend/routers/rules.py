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

    Only the keys present in the request body are updated; all others are preserved.
    """
    if not body.initialValues:
        raise HTTPException(status_code=400, detail="Missing or invalid initialValues")

    config = store.load_rules()
    merged = {**config.initialValues, **body.initialValues}
    updated = RulesConfig(sections=config.sections, initialValues=merged)
    store.save_rules(updated)
    return updated.model_dump()
