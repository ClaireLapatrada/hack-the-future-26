"""
POST /api/events/initiate  — activate a disruption on a shipping lane
POST /api/events/clear     — clear all disruptions (back to OPERATIONAL)
POST /api/events/run       — trigger one full agent detection cycle

Wraps the functions in scripts/initiate_event.py and exposes them over HTTP.

G5: initiate and clear endpoints are rate-limited to 5 requests/minute per IP
    to prevent thrashing the agent pipeline.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Body, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()

# ── In-memory per-IP rate limiter (G5) ───────────────────────────────────────
_RATE_LIMIT = 5          # max requests per window
_RATE_WINDOW = 60.0      # seconds
_rate_counts: dict = defaultdict(list)  # ip → [timestamp, ...]
_rate_lock = threading.Lock()


def _check_rate_limit(client_ip: str) -> None:
    """Raise HTTP 429 if the client has exceeded 5 requests/minute."""
    now = time.time()
    with _rate_lock:
        timestamps = _rate_counts[client_ip]
        # Evict timestamps outside the current window
        _rate_counts[client_ip] = [t for t in timestamps if now - t < _RATE_WINDOW]
        if len(_rate_counts[client_ip]) >= _RATE_LIMIT:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: max {_RATE_LIMIT} requests per {int(_RATE_WINDOW)}s per IP.",
            )
        _rate_counts[client_ip].append(now)


class InitiateEventRequest(BaseModel):
    lane: str = "Asia-Europe (Suez)"
    delay_days: int = 16


class RunAgentRequest(BaseModel):
    prompt: str = (
        "Check for any disruption. Run the full pipeline and output the Supply Chain Operations Briefing."
    )


@router.post("/api/events/initiate")
def initiate_event(request: Request, body: InitiateEventRequest = Body(...)) -> Dict[str, Any]:
    """Set active_disruption.json so the next pipeline run sees a disruption."""
    # G5: Rate limiting
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)
    try:
        from backend.scripts.initiate_event import set_disruption_active
        set_disruption_active(lane=body.lane, delay_days=body.delay_days)
        return {
            "ok": True,
            "lane": body.lane,
            "delay_days": body.delay_days,
            "message": f"Disruption initiated: {body.lane} DISRUPTED, {body.delay_days} day(s) delay.",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/events/clear")
def clear_event(request: Request) -> Dict[str, Any]:
    """Reset active_disruption.json to all-OPERATIONAL state."""
    # G5: Rate limiting
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)
    try:
        from backend.scripts.initiate_event import clear_disruption
        clear_disruption()
        return {"ok": True, "message": "Disruption cleared. All lanes and supplier health are OPERATIONAL."}
    except HTTPException:
        raise
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
