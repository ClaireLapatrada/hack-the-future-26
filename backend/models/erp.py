"""Pydantic models for ERP snapshot (data/mock_erp.json)."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class InventoryItem(BaseModel):
    item_id: str
    description: str
    supplier_id: str
    days_on_hand: float
    daily_consumption: float
    stock_units: int
    on_order_units: int
    expected_delivery_date: Optional[str] = None


class PurchaseOrder(BaseModel):
    po_id: str
    supplier_id: str
    value_usd: float
    delivery_date: Optional[str] = None


class ErpSnapshot(BaseModel):
    inventory: List[InventoryItem] = []
    open_purchase_orders: List[PurchaseOrder] = []
