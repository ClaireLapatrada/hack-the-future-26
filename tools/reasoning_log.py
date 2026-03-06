"""
Agent reasoning stream log — written by the orchestrator agent and runner.
Entries are read by the Next.js UI (GET /api/agent-stream) from ui/data/agent_reasoning_stream.json.

Stream entry types: OBSERVE, ACTION, RESULT, REASON, REASONING, PLANNING, MEMORY, TOOL.
Tool calls are logged with a domain type (perception→OBSERVE, risk→REASONING, etc.) instead of TOOL.

Optional: set TOOL_CALL_DELAY_SECONDS in env to wait before each tool run (helps avoid Gemini rate limit).
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from functools import wraps
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STREAM_LOG_PATH = PROJECT_ROOT / "ui" / "data" / "agent_reasoning_stream.json"

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(PROJECT_ROOT / "orchestrator_agent" / ".env")
except ImportError:
    pass

# Seconds to wait before each tool execution (spreads out calls to stay under rate limit)
try:
    _delay = float(os.getenv("TOOL_CALL_DELAY_SECONDS", "2.5"))
    TOOL_CALL_DELAY_SECONDS = max(0.0, min(30.0, _delay))
except (TypeError, ValueError):
    TOOL_CALL_DELAY_SECONDS = 2.5

# Map tool module to stream tag (no generic TOOL; use domain tag)
_TOOL_MODULE_TO_TYPE = {
    "perception_tools": "OBSERVE",
    "risk_tools": "REASONING",
    "planning_tools": "PLANNING",
    "operational_impact_tools": "REASONING",
    "action_tools": "ACTION",
    "memory_tools": "MEMORY",
}

# Action tool categories for stream UI: PO adjustment, escalation, workflow integration (one-stop mitigation)
_ACTION_TOOL_CATEGORIES = {
    "get_po_adjustment_suggestions": "po_adjustment",
    "submit_restock_for_approval": "po_adjustment",
    "execute_approved_restock": "po_adjustment",
    "escalate_to_management": "escalation",
    "get_client_context": "workflow_integration",
    "get_workflow_integration_status": "workflow_integration",
}

_ALLOWED_TYPES = ("OBSERVE", "ACTION", "RESULT", "REASON", "REASONING", "PLANNING", "MEMORY", "TOOL")

_entries: list[dict] = []


def _time_str() -> str:
    return datetime.now().strftime("%I:%M:%S %p")


def load_entries() -> list[dict]:
    """Load current entries from file (and replace in-memory cache)."""
    global _entries
    if STREAM_LOG_PATH.exists():
        try:
            with open(STREAM_LOG_PATH, encoding="utf-8") as f:
                data = json.load(f)
            _entries = data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            _entries = []
    else:
        _entries = []
    return _entries


def append_entry(
    entry_type: str,
    content: str,
    time_str: Optional[str] = None,
    confidence: Optional[str] = None,
    category: Optional[str] = None,
    meta: Optional[dict] = None,
    detail: Optional[str] = None,
) -> None:
    """Append one entry to the stream log. Types: OBSERVE, ACTION, RESULT, REASON, REASONING, PLANNING, MEMORY, TOOL.
    category: optional 'po_adjustment' | 'escalation' | 'workflow_integration' for action stream labels.
    meta: optional dict e.g. {"documentId": "PLAN-xxx"} for planning document link in stream.
    detail: optional long-form detail (e.g. pretty-printed tool result or calculation breakdown) shown on expand in UI."""
    global _entries
    if entry_type not in _ALLOWED_TYPES:
        entry_type = "OBSERVE"
    entry = {
        "type": entry_type,
        "time": time_str or _time_str(),
        "content": content[:2000] if len(content) > 2000 else content,
    }
    if confidence is not None:
        entry["confidence"] = str(confidence)
    if category is not None:
        entry["category"] = str(category)
    if meta is not None and isinstance(meta, dict):
        entry["meta"] = meta
    if detail is not None:
        # Keep detail reasonably sized; UI shows it on demand.
        entry["detail"] = detail[:8000]
    _entries.append(entry)


def flush() -> None:
    """Write in-memory entries to the JSON file."""
    STREAM_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STREAM_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(_entries, f, indent=2)


def clear() -> None:
    """Clear in-memory log and overwrite file with empty list."""
    global _entries
    _entries = []
    flush()


def get_entries() -> list[dict]:
    """Return current in-memory entries (no file read)."""
    return list(_entries)


def with_reasoning_log(func):
    """Decorator: log domain-specific type for tool call, then RESULT after. Optionally delays before each call to ease rate limits."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        if TOOL_CALL_DELAY_SECONDS > 0:
            time.sleep(TOOL_CALL_DELAY_SECONDS)
        import inspect
        sig = inspect.signature(func)
        try:
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            args_str = ", ".join(f"{k}={repr(v)}" for k, v in bound.arguments.items())
        except Exception:
            args_str = "..."
        tool_call = f"{func.__module__}.{func.__name__}({args_str})"
        # Map module to domain tag (perception→OBSERVE, risk→REASONING, etc.)
        module_name = (func.__module__ or "").split(".")[-1] if func.__module__ else ""
        log_type = _TOOL_MODULE_TO_TYPE.get(module_name, "TOOL")
        category = _ACTION_TOOL_CATEGORIES.get(func.__name__) if log_type == "ACTION" else None
        append_entry(log_type, tool_call, category=category)
        flush()
        try:
            result = func(*args, **kwargs)
            if isinstance(result, dict):
                summary = result.get("status", "") or result.get("message", "")
                if not summary and result:
                    summary = json.dumps(result)[:400]
            else:
                summary = str(result)[:400]
            res_meta = None
            if isinstance(result, dict) and result.get("document_id") and func.__name__ == "create_planning_document":
                res_meta = {"documentId": result["document_id"]}
            # Attach detailed view of tool result so UI can show how calculations/simulations/ranking were done.
            detail = None
            if isinstance(result, dict):
                try:
                    detail = json.dumps(result, indent=2)[:8000]
                except TypeError:
                    # Fallback if result is not fully JSON-serializable
                    detail = str(result)[:8000]
            append_entry("RESULT", summary or "(ok)", category=category, meta=res_meta, detail=detail)
            flush()
            return result
        except Exception as e:
            append_entry("RESULT", f"Error: {e}")
            flush()
            raise

    return wrapper
