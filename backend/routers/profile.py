"""
GET  /api/profile  — read manufacturer_profile.json (with company_info)
POST /api/profile  — write updated manufacturer_profile.json
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

_PROFILE_PATH = Path(__file__).resolve().parent.parent / "config" / "manufacturer_profile.json"


def _load() -> dict:
    with open(_PROFILE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    with open(_PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    # Mirror to frontend/config if it exists
    frontend_copy = (
        Path(__file__).resolve().parent.parent.parent
        / "frontend" / "config" / "manufacturer_profile.json"
    )
    if frontend_copy.parent.exists():
        with open(frontend_copy, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


@router.get("/api/profile")
def get_profile() -> Dict[str, Any]:
    try:
        data = _load()
        if "company_info" not in data:
            data["company_info"] = {
                "company_name": "AutomotiveParts GmbH",
                "contact_email": "supply-ops@automotiveparts.de",
                "sender_name": "Supply Chain Operations Team",
            }
        return data
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


class SupplierModel(BaseModel):
    id: str
    name: str
    category: str
    country: str
    spend_pct: float
    lead_time_days: int
    single_source: bool
    contract_end: str
    health_score: int


class InventoryPolicy(BaseModel):
    target_buffer_days: int
    reorder_threshold_days: int
    max_buffer_days: int


class CustomerSLA(BaseModel):
    customer: str
    on_time_delivery_pct: float
    penalty_per_day_usd: int


class ProductionLine(BaseModel):
    line_id: str
    product: str
    daily_output_units: int
    semiconductor_dependent: bool
    daily_revenue_usd: int


class CompanyInfo(BaseModel):
    company_name: str
    contact_email: str
    sender_name: str


class ProfileUpdateRequest(BaseModel):
    company_info: Optional[CompanyInfo] = None
    suppliers: Optional[List[SupplierModel]] = None
    inventory_policy: Optional[InventoryPolicy] = None
    customer_slas: Optional[List[CustomerSLA]] = None
    production_lines: Optional[List[ProductionLine]] = None


@router.post("/api/profile")
def update_profile(body: ProfileUpdateRequest) -> Dict[str, Any]:
    try:
        data = _load()
        if "company_info" not in data:
            data["company_info"] = {
                "company_name": "AutomotiveParts GmbH",
                "contact_email": "supply-ops@automotiveparts.de",
                "sender_name": "Supply Chain Operations Team",
            }
        if body.company_info is not None:
            data["company_info"] = body.company_info.model_dump()
        if body.suppliers is not None:
            data["suppliers"] = [s.model_dump() for s in body.suppliers]
        if body.inventory_policy is not None:
            data["inventory_policy"] = body.inventory_policy.model_dump()
        if body.customer_slas is not None:
            data["customer_slas"] = [s.model_dump() for s in body.customer_slas]
        if body.production_lines is not None:
            data["production_lines"] = [ln.model_dump() for ln in body.production_lines]
        _save(data)
        return data
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
