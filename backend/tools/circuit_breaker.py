"""
Circuit breaker and budget guard (Phase 7).

CircuitBreaker: prevents cascading failures when a tool repeatedly errors.
BudgetGuard:    caps total committed spend per pipeline session (G1).
"""
from __future__ import annotations

import os
import threading
import time
from enum import Enum
from typing import Dict, Optional


# ── Custom exceptions ──────────────────────────────────────────────────────────

class BudgetExceededError(Exception):
    """Raised when cumulative spend for a pipeline session exceeds the configured cap."""


# ── Circuit breaker ───────────────────────────────────────────────────────────

class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Tripped; calls are blocked
    HALF_OPEN = "half_open" # Probing for recovery


class CircuitBreaker:
    """
    Per-(agent_id, tool_name) circuit breaker.

    States: CLOSED → OPEN after failure_threshold consecutive failures.
    Auto-transitions to HALF_OPEN after reset_timeout_seconds, allowing
    the next call through.  Success resets to CLOSED; failure returns to OPEN.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        reset_timeout_seconds: int = 120,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout_seconds
        self._failures = 0
        self._state = CircuitState.CLOSED
        self._opened_at: float = 0.0
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.time() - self._opened_at >= self._reset_timeout:
                    self._state = CircuitState.HALF_OPEN
            return self._state

    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self._failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_at = time.time()

    def reset(self) -> None:
        with self._lock:
            self._failures = 0
            self._state = CircuitState.CLOSED


# Module-level registry
_breakers: Dict[str, CircuitBreaker] = {}
_breakers_lock = threading.Lock()


def get_breaker(agent_id: str, tool_name: str) -> CircuitBreaker:
    """Return (creating if needed) the CircuitBreaker for (agent_id, tool_name)."""
    key = f"{agent_id}::{tool_name}"
    with _breakers_lock:
        if key not in _breakers:
            _breakers[key] = CircuitBreaker(
                failure_threshold=int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "3")),
                reset_timeout_seconds=int(os.getenv("CIRCUIT_BREAKER_RESET_SECONDS", "120")),
            )
        return _breakers[key]


# ── Budget guard (G1) ─────────────────────────────────────────────────────────

_DEFAULT_MAX_BUDGET = 500_000.0  # $500K per pipeline run by default
_budget_lock = threading.Lock()
_session_spend: Dict[str, float] = {}  # session_id → cumulative USD


def _get_session_id() -> str:
    """Get pipeline session ID from env (set by orchestrator) or thread name."""
    return os.getenv("PIPELINE_SESSION_ID") or threading.current_thread().name


def record_spend(amount_usd: float, session_id: Optional[str] = None) -> None:
    """
    Record committed spend for the current pipeline session.
    Raises BudgetExceededError if cumulative total would exceed the cap.
    """
    sid = session_id or _get_session_id()
    max_budget = float(os.getenv("MAX_PIPELINE_BUDGET_USD", str(_DEFAULT_MAX_BUDGET)))
    with _budget_lock:
        current = _session_spend.get(sid, 0.0)
        new_total = current + amount_usd
        if new_total > max_budget:
            raise BudgetExceededError(
                f"Pipeline budget cap exceeded: ${new_total:,.0f} > ${max_budget:,.0f} "
                f"(session: {sid}). Additional spend blocked."
            )
        _session_spend[sid] = new_total


def get_session_spend(session_id: Optional[str] = None) -> float:
    """Return cumulative spend for the current session."""
    sid = session_id or _get_session_id()
    with _budget_lock:
        return _session_spend.get(sid, 0.0)


def reset_session_budget(session_id: Optional[str] = None) -> None:
    """Reset cumulative spend for a session (call at start of each pipeline run)."""
    sid = session_id or _get_session_id()
    with _budget_lock:
        _session_spend.pop(sid, None)
