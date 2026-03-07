"""
Append-only JSONL audit log (Phase 8).

Every tool execution, write operation, and guardrail block appends one JSON
line to backend/data/audit_log.jsonl.  The file is NEVER truncated by the
application — no clear() method is provided.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, TypedDict

import portalocker

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUDIT_LOG_PATH = PROJECT_ROOT / "data" / "audit_log.jsonl"

_write_lock = threading.Lock()


class AuditEntry(TypedDict, total=False):
    timestamp: str
    agent_id: str
    tool_name: str
    arguments: dict
    outcome: str          # "success" | "error" | "blocked"
    error_message: Optional[str]
    duration_ms: float


def append_audit(entry: AuditEntry) -> None:
    """
    Append one audit entry to audit_log.jsonl.
    Thread-safe. Never truncates the file.
    """
    if "timestamp" not in entry:
        entry["timestamp"] = datetime.now(timezone.utc).isoformat()
    line = json.dumps(entry, default=str)
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _write_lock:
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            portalocker.lock(f, portalocker.LOCK_EX)
            try:
                f.write(line + "\n")
            finally:
                portalocker.unlock(f)


def get_audit_tail(n: int = 100) -> List[AuditEntry]:
    """Return the last N audit entries (for admin display)."""
    if not AUDIT_LOG_PATH.exists():
        return []
    lines: list[str] = []
    with open(AUDIT_LOG_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                lines.append(line)
    tail = lines[-n:] if len(lines) > n else lines
    result = []
    for line in tail:
        try:
            result.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return result
