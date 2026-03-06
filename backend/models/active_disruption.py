"""Pydantic models for active disruption configuration (config/active_disruption.json)."""
from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel


class ShippingLaneStatus(BaseModel):
    status: str
    severity: Optional[str] = None
    avg_delay_days: Optional[int] = None
    reroute_available: Optional[bool] = None
    reroute_via: Optional[str] = None
    reroute_additional_days: Optional[int] = None
    carrier_surcharges_usd_per_teu: Optional[float] = None
    vessels_affected_pct: Optional[float] = None
    last_updated: Optional[str] = None
    source: Optional[str] = None
    articles_found: Optional[int] = None


class ActiveDisruptionConfig(BaseModel):
    active: bool
    supplier_health_degraded: bool = False
    shipping_lanes: Dict[str, ShippingLaneStatus] = {}
