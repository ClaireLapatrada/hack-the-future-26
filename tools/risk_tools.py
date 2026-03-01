"""
Risk Intelligence Tools — Maps disruption signals to operational exposure.
Used by the Risk Intelligence Agent.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
CONFIG_DIR = Path(__file__).parent.parent / "config"


def _load_erp() -> dict:
    with open(DATA_DIR / "mock_erp.json") as f:
        return json.load(f)


def _load_profile() -> dict:
    with open(CONFIG_DIR / "manufacturer_profile.json") as f:
        return json.load(f)


def calculate_revenue_at_risk(
    affected_supplier_id: str,
    estimated_delay_days: int
) -> dict:
    """
    Calculate revenue at risk if a supplier is disrupted for N days.
    Cross-references ERP inventory runway against production line dependencies.

    Args:
        affected_supplier_id: Supplier ID e.g. "SUP-001"
        estimated_delay_days: How many days the disruption might last
    """
    erp = _load_erp()
    profile = _load_profile()

    # Find inventory items from this supplier
    affected_items = [
        item for item in erp["inventory"]
        if item["supplier_id"] == affected_supplier_id
    ]

    # Find production lines dependent on this supplier's items
    at_risk_lines = []
    total_revenue_at_risk = 0
    total_daily_revenue = 0

    for item in affected_items:
        days_on_hand = item["days_on_hand"]
        buffer_after_stock_out = max(0, estimated_delay_days - days_on_hand)

        for line in profile["production_lines"]:
            # Check if line uses this item (simplified: semiconductor items → ECU line)
            if "SEMI" in item["item_id"] and line["semiconductor_dependent"]:
                daily_rev = line["daily_revenue_usd"]
                revenue_at_risk = daily_rev * buffer_after_stock_out
                total_revenue_at_risk += revenue_at_risk
                total_daily_revenue += daily_rev
                at_risk_lines.append({
                    "line_id": line["line_id"],
                    "product": line["product"],
                    "days_on_hand": days_on_hand,
                    "stockout_day": days_on_hand,
                    "production_halt_days": buffer_after_stock_out,
                    "daily_revenue_usd": daily_rev,
                    "revenue_at_risk_usd": revenue_at_risk
                })
            elif "STEEL" in item["item_id"] and not line["semiconductor_dependent"]:
                daily_rev = line["daily_revenue_usd"]
                revenue_at_risk = daily_rev * max(0, estimated_delay_days - days_on_hand)
                total_revenue_at_risk += revenue_at_risk
                total_daily_revenue += daily_rev
                at_risk_lines.append({
                    "line_id": line["line_id"],
                    "product": line["product"],
                    "days_on_hand": days_on_hand,
                    "stockout_day": days_on_hand,
                    "production_halt_days": max(0, estimated_delay_days - days_on_hand),
                    "daily_revenue_usd": daily_rev,
                    "revenue_at_risk_usd": revenue_at_risk
                })

    # SLA penalty calculation
    sla_penalties = 0
    for sla in profile["customer_slas"]:
        halt_days = max(line["production_halt_days"] for line in at_risk_lines) if at_risk_lines else 0
        sla_penalties += sla["penalty_per_day_usd"] * halt_days

    return {
        "status": "success",
        "supplier_id": affected_supplier_id,
        "disruption_duration_days": estimated_delay_days,
        "affected_production_lines": at_risk_lines,
        "total_revenue_at_risk_usd": round(total_revenue_at_risk, 2),
        "sla_penalties_at_risk_usd": round(sla_penalties, 2),
        "total_financial_exposure_usd": round(total_revenue_at_risk + sla_penalties, 2),
        "summary": f"A {estimated_delay_days}-day disruption from {affected_supplier_id} "
                   f"puts ${total_revenue_at_risk:,.0f} in revenue and "
                   f"${sla_penalties:,.0f} in SLA penalties at risk."
    }


def get_inventory_runway(item_id: str) -> dict:
    """
    Get how many days of inventory remain for a specific item.

    Args:
        item_id: ERP item ID e.g. "SEMI-MCU-32"
    """
    erp = _load_erp()
    profile = _load_profile()

    item = next((i for i in erp["inventory"] if i["item_id"] == item_id), None)
    if not item:
        return {"status": "error", "message": f"Item {item_id} not found in ERP"}

    buffer_policy = profile["inventory_policy"]
    days_on_hand = item["days_on_hand"]
    reorder_threshold = buffer_policy["reorder_threshold_days"]
    target_buffer = buffer_policy["target_buffer_days"]

    alert_level = "OK"
    if days_on_hand <= reorder_threshold:
        alert_level = "CRITICAL"
    elif days_on_hand <= target_buffer * 0.5:
        alert_level = "WARNING"
    elif days_on_hand < target_buffer:
        alert_level = "LOW"

    return {
        "status": "success",
        "item_id": item_id,
        "description": item["description"],
        "supplier_id": item["supplier_id"],
        "days_on_hand": days_on_hand,
        "daily_consumption": item["daily_consumption"],
        "stock_units": item["stock_units"],
        "on_order_units": item["on_order_units"],
        "expected_delivery_date": item["expected_delivery_date"],
        "reorder_threshold_days": reorder_threshold,
        "target_buffer_days": target_buffer,
        "alert_level": alert_level,
        "days_until_stockout": days_on_hand,
        "summary": f"{item['description']}: {days_on_hand:.1f} days on hand — Alert: {alert_level}"
    }


def calculate_sla_breach_probability(
    production_halt_days: float,
    customer_name: str
) -> dict:
    """
    Calculate probability of breaching a customer SLA given expected production halt.

    Args:
        production_halt_days: Expected production halt duration
        customer_name: Customer name e.g. "BMW Group"
    """
    profile = _load_profile()
    sla = next((s for s in profile["customer_slas"] if s["customer"] == customer_name), None)

    if not sla:
        return {"status": "error", "message": f"No SLA found for {customer_name}"}

    # Simplified probability model
    breach_probability = min(1.0, production_halt_days * 0.08)
    penalty_exposure = sla["penalty_per_day_usd"] * production_halt_days

    return {
        "status": "success",
        "customer": customer_name,
        "sla_target_pct": sla["on_time_delivery_pct"],
        "production_halt_days": production_halt_days,
        "breach_probability": round(breach_probability, 2),
        "breach_probability_pct": f"{breach_probability * 100:.0f}%",
        "penalty_per_day_usd": sla["penalty_per_day_usd"],
        "total_penalty_exposure_usd": round(penalty_exposure, 2),
        "severity": "CRITICAL" if breach_probability > 0.7 else "HIGH" if breach_probability > 0.4 else "MEDIUM"
    }


def get_supplier_exposure(supplier_id: str) -> dict:
    """
    Get full operational exposure profile for a given supplier.
    Shows spend concentration, lead time, single-source risk.

    Args:
        supplier_id: Supplier ID e.g. "SUP-001"
    """
    profile = _load_profile()
    erp = _load_erp()

    supplier = next((s for s in profile["suppliers"] if s["id"] == supplier_id), None)
    if not supplier:
        return {"status": "error", "message": f"Supplier {supplier_id} not found"}

    # Open POs for this supplier
    open_pos = [po for po in erp["open_purchase_orders"] if po["supplier_id"] == supplier_id]
    total_open_po_value = sum(po["value_usd"] for po in open_pos)

    risk_flags = []
    if supplier["spend_pct"] > 35:
        risk_flags.append(f"HIGH CONCENTRATION: {supplier['spend_pct']}% of total spend")
    if supplier["single_source"]:
        risk_flags.append("SINGLE SOURCE: No qualified backup supplier")
    if supplier["health_score"] < 70:
        risk_flags.append(f"LOW HEALTH SCORE: {supplier['health_score']}/100")
    if supplier["lead_time_days"] > 30:
        risk_flags.append(f"LONG LEAD TIME: {supplier['lead_time_days']} days — low flexibility")

    overall_risk = "CRITICAL" if len(risk_flags) >= 3 else "HIGH" if len(risk_flags) >= 2 else "MEDIUM"

    return {
        "status": "success",
        "supplier": supplier,
        "open_purchase_orders": open_pos,
        "total_open_po_value_usd": total_open_po_value,
        "risk_flags": risk_flags,
        "overall_risk_rating": overall_risk,
        "summary": f"{supplier['name']}: {overall_risk} risk — {len(risk_flags)} flags. "
                   f"${total_open_po_value:,.0f} in open POs at risk."
    }