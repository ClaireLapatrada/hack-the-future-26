"""
Typed data access layer — single source of truth for all JSON file I/O.

Replaces the 5+ scattered copies of _load_profile() / _load_erp() /
_load_active_disruption() across tools/*.py.  Tool files are NOT changed in
this phase; they continue to use their own helpers.  FastAPI routers (Phase 3)
and eventually the tools (Phase 7) will use DataStore instead.

All reads return validated Pydantic models.
All writes serialise from Pydantic models, ensuring the files always conform
to the declared schema.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import List

from backend.models.active_disruption import ActiveDisruptionConfig
from backend.models.approvals import ApprovalEntry, EscalationRecord
from backend.models.disruptions import DisruptionEvent
from backend.models.erp import ErpSnapshot
from backend.models.planning import PlanningDocument
from backend.models.profile import ManufacturerProfile
from backend.models.rules import RulesConfig
from backend.models.stream import StreamEntry
from backend.settings import Settings, settings as _default_settings

# Per-file write locks — prevents concurrent writes corrupting JSON files.
_locks: dict[Path, threading.Lock] = {}


def _lock_for(path: Path) -> threading.Lock:
    if path not in _locks:
        _locks[path] = threading.Lock()
    return _locks[path]


def _read_json(path: Path) -> object:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: object, _operation: str = "write") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock_for(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    # Phase 8: append to audit log after every successful write
    try:
        from backend.tools.audit_log import append_audit
        record_count = len(data) if isinstance(data, list) else 1
        append_audit({
            "agent_id": "data_store",
            "tool_name": _operation,
            "arguments": {"path": str(path), "record_count": record_count},
            "outcome": "success",
            "duration_ms": 0.0,
        })
    except Exception:
        pass


class DataStore:
    """Typed facade over all project JSON files."""

    def __init__(self, cfg: Settings = _default_settings) -> None:
        self._cfg = cfg

    # ── ERP ───────────────────────────────────────────────────────────────

    def load_erp(self) -> ErpSnapshot:
        return ErpSnapshot.model_validate(_read_json(self._cfg.effective_erp_path))

    # ── Manufacturer profile ──────────────────────────────────────────────

    def load_profile(self) -> ManufacturerProfile:
        return ManufacturerProfile.model_validate(
            _read_json(self._cfg.effective_profile_path)
        )

    # ── Active disruption config ──────────────────────────────────────────

    def load_active_disruption(self) -> ActiveDisruptionConfig:
        path = self._cfg.active_disruption_path
        if not path.exists():
            return ActiveDisruptionConfig(active=False)
        return ActiveDisruptionConfig.model_validate(_read_json(path))

    def save_active_disruption(self, config: ActiveDisruptionConfig) -> None:
        _write_json(
            self._cfg.active_disruption_path,
            config.model_dump(),
            _operation="save_active_disruption",
        )

    # ── Disruption history ────────────────────────────────────────────────

    def load_disruption_history(self) -> List[DisruptionEvent]:
        """
        Checks multiple candidate paths in priority order, matching the
        fallback logic already present in tools/risk_tools.py and
        tools/memory_tools.py.
        """
        candidates = [
            self._cfg.disruption_history_path,
            self._cfg.project_root / "mock_disruption_history.json",
            self._cfg.ui_data_dir / "mock_disruption_history.json",
        ]
        for path in candidates:
            if not path.exists():
                continue
            try:
                raw = _read_json(path)
                if isinstance(raw, list):
                    return [DisruptionEvent.model_validate(e) for e in raw]
            except (json.JSONDecodeError, OSError):
                continue
        return []

    def save_disruption_history(self, events: List[DisruptionEvent]) -> None:
        path = self._cfg.disruption_history_path
        _write_json(path, [e.model_dump() for e in events])

    def append_disruption_event(self, event: DisruptionEvent) -> None:
        history = self.load_disruption_history()
        history.append(event)
        self.save_disruption_history(history)

    # ── Pending approvals ─────────────────────────────────────────────────

    def load_pending_approvals(self) -> List[ApprovalEntry]:
        path = self._cfg.pending_approvals_path
        if not path.exists():
            return []
        raw = _read_json(path)
        if not isinstance(raw, list):
            return []
        return [ApprovalEntry.model_validate(a) for a in raw]

    def save_pending_approvals(self, items: List[ApprovalEntry]) -> None:
        _write_json(
            self._cfg.pending_approvals_path,
            [a.model_dump() for a in items],
            _operation="save_pending_approvals",
        )

    def append_approval(self, entry: ApprovalEntry) -> None:
        items = self.load_pending_approvals()
        items.append(entry)
        self.save_pending_approvals(items)

    # ── Escalations ───────────────────────────────────────────────────────

    def load_escalations(self) -> List[EscalationRecord]:
        path = self._cfg.escalations_path
        if not path.exists():
            return []
        raw = _read_json(path)
        if not isinstance(raw, list):
            return []
        return [EscalationRecord.model_validate(e) for e in raw]

    def save_escalations(self, items: List[EscalationRecord]) -> None:
        _write_json(
            self._cfg.escalations_path,
            [e.model_dump() for e in items],
        )

    def append_escalation(self, record: EscalationRecord) -> None:
        items = self.load_escalations()
        items.append(record)
        self.save_escalations(items)

    # ── Planning documents ────────────────────────────────────────────────

    def load_planning_documents(self) -> List[PlanningDocument]:
        path = self._cfg.planning_documents_path
        if not path.exists():
            return []
        raw = _read_json(path)
        if not isinstance(raw, list):
            return []
        return [PlanningDocument.model_validate(d) for d in raw]

    def save_planning_document(self, doc: PlanningDocument) -> None:
        docs = self.load_planning_documents()
        docs.append(doc)
        _write_json(
            self._cfg.planning_documents_path,
            [d.model_dump() for d in docs],
        )

    # ── Agent reasoning stream ────────────────────────────────────────────

    def load_stream(self) -> List[StreamEntry]:
        path = self._cfg.agent_stream_path
        if not path.exists():
            return []
        raw = _read_json(path)
        if not isinstance(raw, list):
            return []
        return [StreamEntry.model_validate(e) for e in raw]

    def save_stream(self, entries: List[StreamEntry]) -> None:
        _write_json(
            self._cfg.agent_stream_path,
            [e.model_dump() for e in entries],
        )

    def append_stream_entry(self, entry: StreamEntry) -> None:
        entries = self.load_stream()
        entries.append(entry)
        self.save_stream(entries)

    # ── Rules config ──────────────────────────────────────────────────────

    def load_rules(self) -> RulesConfig:
        return RulesConfig.model_validate(_read_json(self._cfg.rules_path))

    def save_rules(self, config: RulesConfig) -> None:
        _write_json(self._cfg.rules_path, config.model_dump())

    # ── Action config (unstructured; used by action_tools internals) ──────

    def load_action_config(self) -> dict:
        path = self._cfg.effective_action_config_path
        if not path.exists():
            return {}
        return _read_json(path)  # type: ignore[return-value]

    # ── Planning config (unstructured; loaded by planning_tools at import) ─

    def load_planning_config(self) -> dict:
        return _read_json(self._cfg.effective_planning_config_path)  # type: ignore[return-value]


# ── FastAPI dependency ────────────────────────────────────────────────────────

# Module-level singleton; FastAPI routers inject it via Depends(get_data_store).
_store = DataStore()


def get_data_store() -> DataStore:
    """FastAPI dependency — returns the shared DataStore instance."""
    return _store
