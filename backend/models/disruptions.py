"""Pydantic models for disruption events and display list items."""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class DisruptionImpact(BaseModel):
    delay_days: Optional[int] = None
    revenue_at_risk_usd: Optional[float] = None
    actual_revenue_lost_usd: Optional[float] = None


class MitigationTaken(BaseModel):
    action: str
    cost_usd: Optional[float] = None
    outcome: str


class TimelineEntry(BaseModel):
    time: str
    text: str
    muted: Optional[bool] = None


class DisruptionEvent(BaseModel):
    event_id: str
    date: str
    type: str
    region: str
    severity: str
    affected_suppliers: List[str] = []
    description: str
    impact: Optional[DisruptionImpact] = None
    mitigation_taken: Optional[MitigationTaken] = None
    lessons_learned: Optional[str] = None
    logged_by: Optional[str] = None
    logged_at: Optional[str] = None
    timeline: Optional[List[TimelineEntry]] = None


class DisruptionSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DisruptionListItem(BaseModel):
    id: str
    impact: str
    severity: DisruptionSeverity
    title: str
    tags: List[str]
    description: str
    timeline: List[TimelineEntry]
    source: Optional[str] = None
    url: Optional[str] = None
