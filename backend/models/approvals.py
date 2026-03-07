"""Pydantic models for pending approvals and escalations."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    executed = "executed"


class AuditLogEntry(BaseModel):
    time: str
    text: str


class ApprovalEntry(BaseModel):
    id: str
    type: Optional[str] = None
    severity: str
    title: str
    situation: str
    recommendation: str
    confidence: str
    auditLog: List[AuditLogEntry]
    status: ApprovalStatus
    createdAt: str
    # restock-specific fields
    item_id: Optional[str] = None
    suggested_quantity: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
    adjustment_reason: Optional[str] = None
    # set when executed
    executed_at: Optional[str] = None
    # guardrail fields (Phase 5)
    expires_at: Optional[str] = None          # ISO timestamp; PATCH rejects after this
    approval_count: int = 0                   # for dual-approval enforcement (CRITICAL)


class EscalationRecord(BaseModel):
    id: str
    trigger_reason: str
    severity: str
    problem_summary: str
    suggested_recipients: str
    decision_transparency: Dict[str, Any]
    created_at: str
    status: str
