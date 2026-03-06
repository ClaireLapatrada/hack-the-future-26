"""Pydantic models for manufacturer profile (config/manufacturer_profile.json)."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class Supplier(BaseModel):
    id: str
    name: str
    category: str
    country: str
    spend_pct: float
    lead_time_days: int
    single_source: bool
    contract_end: Optional[str] = None
    health_score: Optional[float] = None


class ProductionLine(BaseModel):
    line_id: str
    product: str
    daily_output_units: Optional[int] = None
    semiconductor_dependent: bool
    daily_revenue_usd: float


class CustomerSLA(BaseModel):
    customer: str
    on_time_delivery_pct: float
    penalty_per_day_usd: float


class InventoryPolicy(BaseModel):
    target_buffer_days: int
    reorder_threshold_days: int
    max_buffer_days: Optional[int] = None


class ManufacturerProfile(BaseModel):
    suppliers: List[Supplier] = []
    production_lines: List[ProductionLine] = []
    customer_slas: List[CustomerSLA] = []
    inventory_policy: InventoryPolicy
