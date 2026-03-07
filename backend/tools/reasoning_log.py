"""
Agent reasoning stream log — written by the orchestrator agent and runner.
Entries are read by the Next.js UI (GET /api/agent-stream) from ui/data/agent_reasoning_stream.json.

Stream entry types: OBSERVE, ACTION, RESULT, REASON, REASONING, PLANNING, MEMORY, TOOL.
Tool calls are logged with a domain type (perception→OBSERVE, risk→REASONING, etc.) instead of TOOL.

Optional: set TOOL_CALL_DELAY_SECONDS in env to wait before each tool run (helps avoid Gemini rate limit).
Optional: set RATE_LIMIT_RPM in env (e.g. 8) to cap requests per minute; see tools/rate_limiter.py.
"""

import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from functools import wraps
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STREAM_LOG_PATH = PROJECT_ROOT / "data" / "agent_reasoning_stream.json"

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(PROJECT_ROOT / "orchestrator_agent" / ".env")
except ImportError:
    pass

try:
    from tools.rate_limiter import wait_if_needed, record_request
except ImportError:
    def wait_if_needed() -> None: ...
    def record_request() -> None: ...

# Seconds to wait before each tool execution (spreads out calls to stay under 15 RPM)
try:
    _delay = float(os.getenv("TOOL_CALL_DELAY_SECONDS", "3"))
    TOOL_CALL_DELAY_SECONDS = max(0.0, min(30.0, _delay))
except (TypeError, ValueError):
    TOOL_CALL_DELAY_SECONDS = 3


def delay_tool_call(func):
    """Decorator that sleeps TOOL_CALL_DELAY_SECONDS before each call. Preserves func signature for ADK AFC."""
    import inspect
    @wraps(func)
    def wrapper(*args, **kwargs):
        wait_if_needed()
        record_request()
        if TOOL_CALL_DELAY_SECONDS > 0:
            time.sleep(TOOL_CALL_DELAY_SECONDS)
        return func(*args, **kwargs)
    try:
        wrapper.__signature__ = inspect.signature(func)
    except Exception:
        pass
    return wrapper


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
_entries_lock = threading.Lock()


def _time_str() -> str:
    return datetime.now().strftime("%I:%M:%S %p")


def load_entries() -> list[dict]:
    """Load current entries from file (and replace in-memory cache)."""
    global _entries
    if STREAM_LOG_PATH.exists():
        try:
            with open(STREAM_LOG_PATH, encoding="utf-8") as f:
                data = json.load(f)
            loaded = data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            loaded = []
    else:
        loaded = []
    with _entries_lock:
        _entries = loaded
    return list(_entries)


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
    with _entries_lock:
        _entries.append(entry)


def flush() -> None:
    """Write in-memory entries to the JSON file."""
    STREAM_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _entries_lock:
        snapshot = list(_entries)
    with open(STREAM_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)


def clear() -> None:
    """Clear in-memory log and overwrite file with empty list."""
    global _entries
    with _entries_lock:
        _entries = []
    flush()


def get_entries() -> list[dict]:
    """Return current in-memory entries (no file read)."""
    with _entries_lock:
        return list(_entries)


def with_reasoning_log(func):
    """
    Decorator: log domain-specific type for tool call, then RESULT after.
    Also integrates:
    - Circuit breaker (Phase 7): blocks calls when a tool has failed repeatedly.
    - Audit log (Phase 8): every call (success or error) is appended to audit_log.jsonl.
    Preserves signature for ADK AFC.
    """
    # Lazy imports to avoid circular import at module load time
    def _get_circuit_breaker(agent_id: str, tool_name: str):
        try:
            from backend.tools.circuit_breaker import get_breaker
            return get_breaker(agent_id, tool_name)
        except Exception:
            return None

    def _audit(agent_id, tool_name, arguments, outcome, error_message=None, duration_ms=0.0):
        try:
            from backend.tools.audit_log import append_audit
            entry = {
                "agent_id": agent_id,
                "tool_name": tool_name,
                "arguments": arguments,
                "outcome": outcome,
                "duration_ms": duration_ms,
            }
            if error_message is not None:
                entry["error_message"] = error_message
            append_audit(entry)
        except Exception:
            pass

    @wraps(func)
    def wrapper(*args, **kwargs):
        wait_if_needed()
        record_request()
        if TOOL_CALL_DELAY_SECONDS > 0:
            time.sleep(TOOL_CALL_DELAY_SECONDS)
        import inspect
        sig = inspect.signature(func)
        try:
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            args_str = ", ".join(f"{k}={repr(v)}" for k, v in bound.arguments.items())
            bound_args = dict(bound.arguments)
        except Exception:
            args_str = "..."
            bound_args = {}
        tool_call = f"{func.__module__}.{func.__name__}({args_str})"
        # Map module to domain tag (perception→OBSERVE, risk→REASONING, etc.)
        module_name = (func.__module__ or "").split(".")[-1] if func.__module__ else ""
        log_type = _TOOL_MODULE_TO_TYPE.get(module_name, "TOOL")
        category = _ACTION_TOOL_CATEGORIES.get(func.__name__) if log_type == "ACTION" else None

        # Circuit breaker check
        agent_id = module_name or "unknown"
        tool_name = func.__name__
        cb = _get_circuit_breaker(agent_id, tool_name)
        if cb and cb.is_open():
            err_msg = f"Circuit breaker OPEN for {agent_id}.{tool_name} — too many consecutive failures."
            append_entry(log_type, tool_call, category=category)
            append_entry("RESULT", f"Error: {err_msg}")
            flush()
            _audit(agent_id, tool_name, bound_args, "blocked", error_message=err_msg)
            raise RuntimeError(err_msg)

        append_entry(log_type, tool_call, category=category)
        flush()
        _t0 = time.time()
        try:
            result = func(*args, **kwargs)
            duration_ms = (time.time() - _t0) * 1000
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
                    detail = str(result)[:8000]
            append_entry("RESULT", summary or "(ok)", category=category, meta=res_meta, detail=detail)
            flush()
            # Record circuit breaker success and write audit entry
            if cb:
                cb.record_success()
            outcome = "error" if (isinstance(result, dict) and result.get("status") == "error") else "success"
            _audit(agent_id, tool_name, bound_args, outcome, duration_ms=duration_ms)
            return result
        except Exception as e:
            duration_ms = (time.time() - _t0) * 1000
            append_entry("RESULT", f"Error: {e}")
            flush()
            if cb:
                cb.record_failure()
            _audit(agent_id, tool_name, bound_args, "error", error_message=str(e), duration_ms=duration_ms)
            raise

    import inspect
    try:
        wrapper.__signature__ = inspect.signature(func)
    except Exception:
        pass
    return wrapper
