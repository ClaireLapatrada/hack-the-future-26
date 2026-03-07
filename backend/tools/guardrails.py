"""
Guardrails — shared sanitization, validation, and coherence utilities (Phases 1-3, 9).

Used across tool modules to enforce security policies in code rather than prompts.
Import this module instead of duplicating logic in individual tool files.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from time import time
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


# ── Custom exceptions ──────────────────────────────────────────────────────────

class GuardrailBlockedError(Exception):
    """Raised when a guardrail blocks an action from executing."""


class ToolValidationError(ValueError):
    """Raised when a tool receives invalid input arguments."""


class StaleDataWarning(UserWarning):
    """Emitted when a data file is older than the configured freshness threshold."""


# ── Prompt injection patterns ─────────────────────────────────────────────────

_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(previous|prior|all|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an|the)\s+", re.IGNORECASE),
    re.compile(r"\bsystem\s*:\s*", re.IGNORECASE),
    re.compile(r"\bassistant\s*:\s*", re.IGNORECASE),
    re.compile(r"forget\s+(your|all|previous)", re.IGNORECASE),
    re.compile(r"disregard\s+(your|all|previous|the)\s+(instructions?|rules?|constraints?)", re.IGNORECASE),
    re.compile(r"new\s+instruction\s*:", re.IGNORECASE),
    re.compile(r"<\s*(system|user|assistant|instruction)\s*>", re.IGNORECASE),
    re.compile(r"\[\s*(system|instruction|override)\s*\]", re.IGNORECASE),
    re.compile(r"pretend\s+(you\s+are|to\s+be)", re.IGNORECASE),
    re.compile(r"act\s+as\s+(if\s+you\s+(are|were)|a[n]?\s+)", re.IGNORECASE),
    re.compile(r"override\s+(your\s+)?(safety|security|guidelines?|constraints?)", re.IGNORECASE),
    re.compile(r"\bjailbreak\b", re.IGNORECASE),
    re.compile(r"\bDAN\s+mode\b", re.IGNORECASE),
    re.compile(r"reveal\s+(your\s+)?(system\s+prompt|instructions?|training)", re.IGNORECASE),
]

# ── Supply chain relevance keywords ───────────────────────────────────────────

_SUPPLY_CHAIN_KEYWORDS = [
    "ship", "shipping", "freight", "logistics", "port", "cargo", "vessel", "container",
    "supplier", "supply", "inventory", "restock", "procurement", "purchase", "order",
    "disruption", "delay", "shortage", "semiconductor", "component", "parts",
    "climate", "weather", "flood", "typhoon", "earthquake", "storm",
    "geopolit", "sanction", "tariff", "trade", "border",
    "factory", "manufacturer", "production", "assembly", "plant",
    "lane", "route", "transit", "suez", "red sea", "panama",
    "taiwan", "vietnam", "germany", "poland", "asia", "europe",
    "automotive", "steel", "plastic", "electronic",
]

# ── Internal data patterns to redact from supplier-facing content (G4) ────────

_FINANCIAL_PATTERNS = [
    # Dollar amounts with optional unit: $50K, $1.2M, $500,000
    re.compile(r'\$\s*\d[\d,]*(?:\.\d+)?\s*[KMBkmb]?\b'),
    # SLA penalty references with amounts
    re.compile(
        r'\b(sla\s+penalty|penalty\s+of|penalties?)\s*[:\-]?\s*\$?\s*\d[\d,]*(?:\.\d+)?\s*[KMBkmb]?\b',
        re.IGNORECASE,
    ),
    # Exact inventory counts in context
    re.compile(r'\b\d[\d,]+\s+units?\s+(on hand|in stock|available|remaining)\b', re.IGNORECASE),
    # Revenue figures
    re.compile(r'\brevenue[^\n]{0,30}\$\s*\d[\d,]*(?:\.\d+)?\s*[KMBkmb]?\b', re.IGNORECASE),
]


def sanitize_external_content(text: str, max_chars: int = 2000) -> str:
    """
    Strip control characters, neutralise prompt-injection patterns, and truncate.
    Returns sanitized text safe to embed in agent prompts.
    """
    if not text:
        return ""
    # Remove non-printable control chars (keep \\n, \\r, \\t)
    cleaned = "".join(
        ch for ch in text
        if unicodedata.category(ch) not in ("Cc", "Cf") or ch in "\n\r\t"
    )
    # Detect and neutralise injection patterns
    injection_found = False
    for pat in _INJECTION_PATTERNS:
        if pat.search(cleaned):
            injection_found = True
            cleaned = pat.sub("[CONTENT REMOVED]", cleaned)

    if injection_found:
        logger.warning("Prompt injection pattern detected and neutralised in external content.")
        try:
            from backend.tools.audit_log import append_audit
            append_audit({
                "agent_id": "guardrails",
                "tool_name": "sanitize_external_content",
                "arguments": {},
                "outcome": "blocked",
                "error_message": "Prompt injection pattern detected and neutralised",
                "duration_ms": 0.0,
            })
        except Exception:
            pass

    return cleaned[:max_chars]


def validate_supply_chain_relevance(text: str) -> bool:
    """
    Return True if text contains supply-chain terminology, False otherwise.
    Used to filter out off-topic external content before passing to agents.
    """
    if not text:
        return False
    lower = text.lower()
    return any(kw in lower for kw in _SUPPLY_CHAIN_KEYWORDS)


def redact_internal_data(text: str) -> Tuple[str, bool]:
    """
    Redact internal financial figures, SLA penalty amounts, and exact inventory
    counts from text destined for external parties (e.g. supplier emails).
    Returns (redacted_text, was_redacted).
    """
    redacted = text
    was_redacted = False
    for pat in _FINANCIAL_PATTERNS:
        if pat.search(redacted):
            redacted = pat.sub("[REDACTED]", redacted)
            was_redacted = True
    if was_redacted:
        logger.info("Internal data redacted from supplier-facing content.")
    return redacted, was_redacted


def check_data_freshness(path: Path, max_age_hours: float = 48.0) -> bool:
    """
    Return True if the file's mtime is within max_age_hours; False if stale or missing.
    A False return means the caller should emit a StaleDataWarning.
    """
    if not path.exists():
        return False
    age_seconds = time() - path.stat().st_mtime
    return (age_seconds / 3600.0) <= max_age_hours


# ── Pipeline coherence / contradiction detection (G7) ────────────────────────

@dataclass
class CoherenceResult:
    coherent: bool
    reason: str
    recommendation: str = field(default="")


def validate_pipeline_coherence(
    threat_level: str,
    inventory_runway_days: int,
    revenue_at_risk_usd: float,
) -> CoherenceResult:
    """
    Detect contradictions between asserted threat level and supporting evidence.
    Returns CoherenceResult with coherent=False if the combination is implausible.

    Called by the orchestrator before the action step to catch hallucinated urgency.
    """
    threat = (threat_level or "").upper()

    # CRITICAL threat but strong inventory and low revenue impact
    if threat == "CRITICAL" and inventory_runway_days > 30 and revenue_at_risk_usd < 100_000:
        return CoherenceResult(
            coherent=False,
            reason=(
                f"CRITICAL threat asserted but inventory runway is {inventory_runway_days}d (>30d) "
                f"and revenue at risk is only ${revenue_at_risk_usd:,.0f} (<$100K). "
                "Evidence does not support CRITICAL classification."
            ),
            recommendation="Require human confirmation before proceeding to action step.",
        )

    # LOW threat but critically depleted inventory
    if threat == "LOW" and inventory_runway_days < 5:
        return CoherenceResult(
            coherent=False,
            reason=(
                f"LOW threat asserted but inventory runway is {inventory_runway_days}d (<5d), "
                "which is critically low. Threat level may be under-stated."
            ),
            recommendation="Escalate for human review — inventory runway is critical.",
        )

    return CoherenceResult(
        coherent=True,
        reason="Assessment is coherent with supporting evidence.",
    )


# ── Input validation helpers (Phase 2) ────────────────────────────────────────

_SEVERITY_VALUES = frozenset({"LOW", "MEDIUM", "HIGH", "CRITICAL"})
_RISK_APPETITE_VALUES = frozenset({"low", "medium", "high"})
_SUPPLIER_ID_RE = re.compile(r'^SUP-\d{3}$')
_ITEM_ID_RE = re.compile(r'^[A-Z]{2,}-[A-Z]{2,}-\d{2,}$')
_SCENARIO_TYPE_VALUES = frozenset({
    "airfreight", "alternate_supplier", "buffer_build", "spot_market", "demand_deferral"
})


def validate_severity(value: str, field_name: str = "severity") -> str:
    """Validate severity enum value. Raises ToolValidationError on bad input."""
    upper = (value or "").upper()
    if upper not in _SEVERITY_VALUES:
        raise ToolValidationError(
            f"Invalid {field_name}='{value}'. Must be one of {sorted(_SEVERITY_VALUES)}."
        )
    return upper


def validate_supplier_id(value: str) -> str:
    """Validate SUP-NNN format supplier ID."""
    if not _SUPPLIER_ID_RE.match(value or ""):
        raise ToolValidationError(
            f"Invalid supplier_id='{value}'. Expected format: SUP-NNN (e.g. SUP-001)."
        )
    return value


def validate_item_id(value: str) -> str:
    """Validate item ID format like SEMI-MCU-32."""
    if not _ITEM_ID_RE.match(value or ""):
        raise ToolValidationError(
            f"Invalid item_id='{value}'. Expected format: ALPHA-ALPHA-NUM (e.g. SEMI-MCU-32)."
        )
    return value


def validate_cost_usd(value: float, field_name: str = "estimated_cost_usd") -> float:
    """Validate cost is non-negative and within sanity ceiling."""
    if not isinstance(value, (int, float)) or value < 0:
        raise ToolValidationError(f"{field_name} must be >= 0, got {value!r}.")
    if value > 10_000_000:
        raise ToolValidationError(f"{field_name}={value:,.0f} exceeds $10M sanity ceiling.")
    return float(value)


def validate_quantity(value: int, field_name: str = "suggested_quantity") -> int:
    """Validate quantity is a positive integer within sane bounds."""
    if not isinstance(value, int) or value < 1:
        raise ToolValidationError(f"{field_name} must be >= 1, got {value!r}.")
    if value > 100_000:
        raise ToolValidationError(f"{field_name}={value} exceeds 100,000 sanity ceiling.")
    return value


def validate_probability(value: float, field_name: str = "probability_pct") -> float:
    """Validate a percentage is 0-100."""
    if not isinstance(value, (int, float)) or not (0 <= value <= 100):
        raise ToolValidationError(f"{field_name} must be 0-100, got {value!r}.")
    return float(value)
