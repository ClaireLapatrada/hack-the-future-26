"""
POST /api/events/initiate  — activate a disruption on a shipping lane
POST /api/events/clear     — clear all disruptions (back to OPERATIONAL)
POST /api/events/run       — trigger one full agent detection cycle

Wraps the functions in scripts/initiate_event.py and exposes them over HTTP.
"""
from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

router = APIRouter()


class InitiateEventRequest(BaseModel):
    lane: str = "Asia-Europe (Suez)"
    delay_days: int = 16


class RunAgentRequest(BaseModel):
    prompt: str = (
        "Check for any disruption. Run the full pipeline and output the Supply Chain Operations Briefing."
    )


@router.post("/api/events/initiate")
def initiate_event(body: InitiateEventRequest = Body(...)) -> Dict[str, Any]:
    """Set active_disruption.json so the next pipeline run sees a disruption."""
    try:
        from backend.scripts.initiate_event import set_disruption_active
        set_disruption_active(lane=body.lane, delay_days=body.delay_days)
        return {
            "ok": True,
            "lane": body.lane,
            "delay_days": body.delay_days,
            "message": f"Disruption initiated: {body.lane} DISRUPTED, {body.delay_days} day(s) delay.",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/events/clear")
def clear_event() -> Dict[str, Any]:
    """Reset active_disruption.json to all-OPERATIONAL state."""
    try:
        from backend.scripts.initiate_event import clear_disruption
        clear_disruption()
        return {"ok": True, "message": "Disruption cleared. All lanes and supplier health are OPERATIONAL."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/events/run")
def run_agent(body: RunAgentRequest = Body(...)) -> Dict[str, Any]:
    """
    Trigger one full agent detection cycle synchronously.

    This is a long-running call (may take minutes). Prefer using the async
    pipeline runner for production use.
    """
    try:
        from backend.scripts.initiate_event import _run_one_cycle
        _run_one_cycle(prompt=body.prompt)
        return {"ok": True, "message": "Agent cycle complete. Check /api/agent-stream for results."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
