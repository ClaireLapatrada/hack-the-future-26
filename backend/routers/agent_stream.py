"""
GET /api/agent-stream

Serves the agent reasoning stream. Supports context and eventId query params
for per-context or per-event stream files; falls back to the default stream.
Mirrors the logic in ui/app/api/agent-stream/route.ts.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.data import DataStore, get_data_store
from backend.models.stream import StreamEntry, StreamEntryType
from backend.settings import settings

router = APIRouter()

_VALID_TYPES = {e.value for e in StreamEntryType}


def _normalize_entry(raw: dict) -> Optional[StreamEntry]:
    """Validate and normalise one raw stream entry. Returns None if invalid."""
    if not isinstance(raw, dict) or not isinstance(raw.get("content"), str):
        return None
    entry_type = raw.get("type", "OBSERVE")
    if entry_type not in _VALID_TYPES:
        entry_type = "OBSERVE"
    time_val = raw.get("time", "—")
    if not isinstance(time_val, str):
        time_val = "—"
    return StreamEntry(
        type=entry_type,
        time=time_val,
        content=raw["content"],
        confidence=str(raw["confidence"]) if raw.get("confidence") is not None else None,
        category=str(raw["category"]) if raw.get("category") is not None else None,
        meta=raw.get("meta") if isinstance(raw.get("meta"), dict) else None,
        detail=raw["detail"] if isinstance(raw.get("detail"), str) else None,
    )


@router.get("/api/agent-stream", response_model=List[StreamEntry])
def get_agent_stream(
    context: str = Query(default="dashboard"),
    eventId: Optional[str] = Query(default=None),
    store: DataStore = Depends(get_data_store),
) -> List[StreamEntry]:
    """
    Return agent reasoning stream entries, newest first.

    Checks for a context-specific stream file before falling back to the default.
    """
    import json

    ui_data_dir = settings.ui_data_dir

    # Resolve context-specific path (same logic as the TS route)
    default_path = ui_data_dir / "agent_reasoning_stream.json"
    if context == "disruption" and eventId:
        context_path = ui_data_dir / f"agent_reasoning_stream_disruption_{eventId}.json"
    elif context == "disruption":
        context_path = ui_data_dir / "agent_reasoning_stream_disruption.json"
    else:
        context_path = default_path

    stream_path = context_path if context_path.exists() else default_path

    if not stream_path.exists():
        return []

    try:
        raw_list = json.loads(stream_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise HTTPException(status_code=500, detail="Failed to load agent reasoning stream") from exc

    if not isinstance(raw_list, list):
        return []

    entries: List[StreamEntry] = []
    for raw in raw_list:
        entry = _normalize_entry(raw)
        if entry is not None:
            entries.append(entry)

    # Newest first
    entries.reverse()
    return entries
