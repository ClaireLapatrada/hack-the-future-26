"""
Risk Intelligence Tools — Maps disruption signals to operational exposure.
Used by the Risk Intelligence Agent.

Implements the Risk Intelligence Engine guideline:
- Disruption probability scoring: P(disruption) over a time horizon using risk indicators
  (supplier delivery delay frequency, financial health, region instability, logistics congestion,
  weather disruption probability) combined via a weighted probability model.
- Output: supplier name, disruption probability (0–100%), risk classification (Low/Medium/High),
  primary drivers.

By default, these tools read from in-repo mock data:
- data/mock_erp.json
- config/manufacturer_profile.json
- data/mock_disruption_history.json (or project root)

To feed **real** ERP and manufacturer data without changing code, you can
point them at your own JSON exports via environment variables:
- ERP_JSON_PATH: absolute or relative path to an ERP snapshot JSON
- MANUFACTURER_PROFILE_PATH: path to a manufacturer profile JSON

If the env vars are not set, the tools fall back to the bundled mock files.
"""

import json
import os
from pathlib import Path
from typing import Optional

from backend.models.tool_results import (
    DisruptionProbabilityResult,
    InventoryRunwayResult,
    RevenueAtRiskExecutiveResult,
    RevenueAtRiskResult,
    SlaBreachResult,
    SupplierExposureResult,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Trained model (optional). Train with: python scripts/train_risk_model.py --csv data.csv
RISK_MODEL_PATH = DATA_DIR / "risk_model.joblib"
RISK_MODEL_META_PATH = DATA_DIR / "risk_model_features.json"
RISK_FEATURE_ORDER = [
    "financial_health_risk",
    "delivery_delay_frequency",
    "region_instability",
    "logistics_congestion",
    "weather_disruption_prob",
    "single_source",
    "spend_pct",
]

_cached_risk_model = None
_cached_risk_meta = None


def _load_risk_model():
    """Load trained classifier and meta if available. Cached for reuse."""
    global _cached_risk_model, _cached_risk_meta
    if _cached_risk_model is not None:
        return _cached_risk_model, _cached_risk_meta
    try:
        import joblib
    except ImportError:
        return None, None
    if not RISK_MODEL_PATH.exists() or not RISK_MODEL_META_PATH.exists():
        return None, None
    try:
        _cached_risk_model = joblib.load(RISK_MODEL_PATH)
        with open(RISK_MODEL_META_PATH, encoding="utf-8") as f:
            _cached_risk_meta = json.load(f)
        return _cached_risk_model, _cached_risk_meta
    except Exception:
        return None, None


def _load_erp() -> dict:
    """
    Load ERP snapshot.

    Order of precedence:
    1) ERP_JSON_PATH env var (if set)
    2) data/mock_erp.json (repo default)
    """
    env_path = os.getenv("ERP_JSON_PATH")
    path = Path(env_path) if env_path else DATA_DIR / "mock_erp.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_profile() -> dict:
    """
    Load manufacturer profile.

    Order of precedence:
    1) MANUFACTURER_PROFILE_PATH env var (if set)
    2) config/manufacturer_profile.json (repo default)
    """
    env_path = os.getenv("MANUFACTURER_PROFILE_PATH")
    path = Path(env_path) if env_path else CONFIG_DIR / "manufacturer_profile.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def calculate_revenue_at_risk(
    affected_supplier_id: str,
    estimated_delay_days: int
) -> RevenueAtRiskResult:
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


def get_inventory_runway(item_id: str) -> InventoryRunwayResult:
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
) -> SlaBreachResult:
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


def get_supplier_exposure(supplier_id: str) -> SupplierExposureResult:
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


def _load_disruption_history() -> list:
    """Load disruption event history from data/ or project root for delivery delay frequency."""
    for p in [DATA_DIR / "mock_disruption_history.json", PROJECT_ROOT / "mock_disruption_history.json"]:
        if p.exists():
            try:
                with open(p, encoding="utf-8") as f:
                    data = json.load(f)
                return data if isinstance(data, list) else []
            except (json.JSONDecodeError, OSError):
                continue
    ui_data = PROJECT_ROOT / "ui" / "data" / "mock_disruption_history.json"
    if ui_data.exists():
        try:
            with open(ui_data, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _load_active_disruption() -> dict:
    """Load config/active_disruption.json for lane status and supplier_health_degraded."""
    for p in [CONFIG_DIR / "active_disruption.json", PROJECT_ROOT / "config" / "active_disruption.json"]:
        if p.exists():
            try:
                with open(p, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
    return {"active": False, "supplier_health_degraded": False, "shipping_lanes": {}}


def get_disruption_probability(
    supplier_id: str,
    time_horizon_days: int = 30,
    news_signals_json: Optional[str] = None,
    climate_alerts_json: Optional[str] = None,
    shipping_lane_status_json: Optional[str] = None,
    supplier_health_json: Optional[str] = None,
) -> DisruptionProbabilityResult:
    """
    Disruption probability scoring per Risk Intelligence Engine guideline.

    Estimates P(disruption) for a supplier over a time horizon using:
    - Risk indicators: supplier delivery delay frequency, supplier financial health score,
      region instability index, logistics congestion score, weather disruption probability.
    - A weighted probability model (can be replaced with supervised learning e.g. Gradient Boosting,
      Logistic Regression, Random Forest when training data is available).

    Inputs (used when provided or from internal data):
    - Global news / geopolitical: news_signals_json or derived from disruption history
    - Weather/climate: climate_alerts_json
    - Shipping congestion: shipping_lane_status_json or config/active_disruption
    - Supplier financial / historical: manufacturer_profile, supplier_health_json, ERP, disruption history

    Output: supplier name, disruption probability (0–100%), risk classification (Low/Medium/High),
    primary drivers.

    Args:
        supplier_id: Supplier ID e.g. "SUP-001"
        time_horizon_days: Time horizon for probability (e.g. 30 days)
        news_signals_json: Optional JSON string of news/signal results from search_disruption_news
        climate_alerts_json: Optional JSON string of climate alert results from get_climate_alerts
        shipping_lane_status_json: Optional JSON string of lane status from get_shipping_lane_status
        supplier_health_json: Optional JSON string of health from score_supplier_health
    """
    profile = _load_profile()
    erp = _load_erp()
    history = _load_disruption_history()
    active = _load_active_disruption()

    supplier = next((s for s in profile.get("suppliers") or [] if s.get("id") == supplier_id), None)
    if not supplier:
        return {"status": "error", "message": f"Supplier {supplier_id} not found"}

    supplier_name = supplier.get("name") or supplier_id
    region = (supplier.get("country") or "Unknown").lower()
    health_score = supplier.get("health_score")
    lead_time_days = supplier.get("lead_time_days") or 30
    single_source = supplier.get("single_source", False)
    spend_pct = supplier.get("spend_pct") or 0

    # Parse optional external signals
    news_signals = []
    if news_signals_json:
        try:
            data = json.loads(news_signals_json)
            news_signals = data.get("signals") or data.get("articles_found") or []
            if isinstance(news_signals, int):
                news_signals = []
        except (TypeError, json.JSONDecodeError):
            pass

    climate_alerts = {}
    if climate_alerts_json:
        try:
            data = json.loads(climate_alerts_json)
            climate_alerts = data.get("alerts") or {}
        except (TypeError, json.JSONDecodeError):
            pass

    lane_disrupted = False
    lane_severity = "Low"
    if shipping_lane_status_json:
        try:
            data = json.loads(shipping_lane_status_json)
            lane_status = data.get("lane_status") or data
            if lane_status.get("status") == "DISRUPTED":
                lane_disrupted = True
                lane_severity = lane_status.get("severity") or "High"
        except (TypeError, json.JSONDecodeError):
            pass
    if not lane_disrupted and active.get("active") and active.get("shipping_lanes"):
        for lane_data in (active.get("shipping_lanes") or {}).values():
            if isinstance(lane_data, dict) and lane_data.get("status") == "DISRUPTED":
                lane_disrupted = True
                lane_severity = lane_data.get("severity") or "High"
                break

    if supplier_health_json:
        try:
            data = json.loads(supplier_health_json)
            h = data.get("health_data") or data
            if isinstance(h, dict) and h.get("overall_health_score") is not None:
                health_score = int(h["overall_health_score"])
        except (TypeError, json.JSONDecodeError, ValueError):
            pass

    # ---- Risk indicators (0–1 scale for probability model) ----
    # 1. Supplier delivery delay frequency (from historical disruption events)
    supplier_events = [
        e for e in history
        if e.get("affected_suppliers") and supplier_id in e.get("affected_suppliers", [])
    ]
    delay_events = [
        e for e in supplier_events
        if ((e.get("impact") or {}).get("delay_days") or 0) > 0
    ]
    total_events = max(len(supplier_events), 1)
    delivery_delay_frequency = min(1.0, len(delay_events) / total_events * 2)  # 0–1

    # 2. Supplier financial health score (invert: low health = high risk)
    if health_score is None:
        health_score = 75
    health_score = max(0, min(100, int(health_score)))
    financial_health_risk = 1.0 - (health_score / 100.0)

    # 3. Region instability index (from climate alerts + news for region)
    region_alerts = climate_alerts.get(supplier.get("country") or "", {}).get("active_alerts") or []
    region_instability = min(1.0, (len(region_alerts) * 0.2) + (len(news_signals) * 0.05))
    if "taiwan" in region or "vietnam" in region:
        region_instability = min(1.0, region_instability + 0.2)  # base geopolitical lift

    # 4. Logistics congestion score (shipping lane disrupted)
    logistics_congestion = 0.7 if lane_disrupted and lane_severity == "High" else (0.4 if lane_disrupted else 0.0)

    # 5. Weather disruption probability (from climate alerts in region)
    weather_disruption_prob = min(1.0, len(region_alerts) * 0.15)

    # ---- Use trained classifier if available, else weighted formula ----
    spend_pct_scaled = min(1.0, (spend_pct or 0) / 100.0)
    single_source_float = 1.0 if single_source else 0.0
    feature_vector = [
        financial_health_risk,
        delivery_delay_frequency,
        region_instability,
        logistics_congestion,
        weather_disruption_prob,
        single_source_float,
        spend_pct_scaled,
    ]
    use_model = False
    model, meta = _load_risk_model()
    if model is not None and meta is not None:
        try:
            import numpy as np
            X = np.array([feature_vector], dtype=np.float64)
            proba = model.predict_proba(X)[0]
            pred_class = int(model.predict(X)[0])
            classes = meta.get("classes", ["Low", "Medium", "High"])
            risk_classification = classes[pred_class] if pred_class < len(classes) else "Medium"
            p_low = proba[0] if len(proba) > 0 else 0.33
            p_med = proba[1] if len(proba) > 1 else 0.33
            p_high = proba[2] if len(proba) > 2 else 0.34
            p_disruption = p_low * 0.15 + p_med * 0.50 + p_high * 0.85
            disruption_probability_pct = round(float(p_disruption) * 100, 1)
            use_model = True
        except Exception:
            pass
    if not use_model:
        w_health = 0.25
        w_region = 0.25
        w_logistics = 0.25
        w_delivery = 0.15
        w_weather = 0.10
        p_disruption = (
            w_health * financial_health_risk
            + w_region * region_instability
            + w_logistics * logistics_congestion
            + w_delivery * delivery_delay_frequency
            + w_weather * weather_disruption_prob
        )
        if single_source:
            p_disruption = min(1.0, p_disruption * 1.15)
        if spend_pct > 35:
            p_disruption = min(1.0, p_disruption * 1.1)
        disruption_probability_pct = round(p_disruption * 100, 1)
        if disruption_probability_pct < 35:
            risk_classification = "Low"
        elif disruption_probability_pct < 65:
            risk_classification = "Medium"
        else:
            risk_classification = "High"

    # Primary drivers (key factors contributing to the score)
    primary_drivers = []
    if financial_health_risk > 0.4:
        primary_drivers.append(f"Supplier financial health score ({health_score}/100)")
    if region_instability > 0.3:
        primary_drivers.append(f"Region instability / geopolitical exposure ({supplier.get('country') or 'N/A'})")
    if logistics_congestion > 0.3:
        primary_drivers.append("Logistics congestion / shipping lane disruption")
    if delivery_delay_frequency > 0.3:
        primary_drivers.append(f"Historical delivery delay frequency ({len(delay_events)} events)")
    if weather_disruption_prob > 0.2:
        primary_drivers.append("Weather / natural disaster alerts in region")
    if single_source:
        primary_drivers.append("Single-source supplier (no qualified backup)")
    if spend_pct > 35:
        primary_drivers.append(f"High spend concentration ({spend_pct}%)")
    if not primary_drivers:
        primary_drivers.append("Baseline risk from profile and history")

    return {
        "status": "success",
        "supplier_id": supplier_id,
        "supplier_name": supplier_name,
        "time_horizon_days": time_horizon_days,
        "disruption_probability_pct": disruption_probability_pct,
        "risk_classification": risk_classification,
        "primary_drivers": primary_drivers,
        "risk_indicators": {
            "supplier_delivery_delay_frequency": round(delivery_delay_frequency, 3),
            "supplier_financial_health_score": health_score,
            "region_instability_index": round(region_instability, 3),
            "logistics_congestion_score": round(logistics_congestion, 3),
            "weather_disruption_probability": round(weather_disruption_prob, 3),
        },
        "summary": (
            f"{supplier_name}: {disruption_probability_pct}% disruption probability ({time_horizon_days}d) — "
            f"{risk_classification}. Key drivers: {'; '.join(primary_drivers[:3])}."
        ),
    }


def estimate_revenue_at_risk_executive(operational_impact_json: Optional[str] = None) -> RevenueAtRiskExecutiveResult:
    """
    Revenue-at-risk estimation for executives. Quantifies financial exposure from operational disruption.

    Links operations to revenue via production lines and customer SLAs. Uses operational impact
    (downtime probability, affected lines, delay range) to estimate lost production and SLA penalties.
    Includes margin impact and customer service-level risk. Returns best, expected, and worst-case outcomes.

    Args:
        operational_impact_json: Optional JSON string from get_operational_impact(); if not provided, calls it internally.
            Can be the full return (with status) or a payload with production_downtime_probability_pct,
            affected_production_lines, estimated_delay_days_min/max, summary.

    Returns:
        revenue_at_risk_usd: Expected revenue at risk.
        margin_impact_usd: Estimated margin impact (revenue_at_risk × margin rate).
        sla_penalties_usd: Estimated SLA penalties from delay.
        customers_affected: Number of major customer accounts at risk.
        best_case, expected_case, worst_case: Outcomes keyed by delay (min/mid/max).
        summary: Human-readable executive summary.
    """
    from tools.operational_impact_tools import get_operational_impact

    profile = _load_profile()
    from_json = False
    if operational_impact_json:
        try:
            impact = json.loads(operational_impact_json)
            if isinstance(impact, dict):
                from_json = True
            else:
                impact = get_operational_impact()
        except (TypeError, json.JSONDecodeError):
            impact = get_operational_impact()
    else:
        impact = get_operational_impact()

    # Only require status when impact came from get_operational_impact(); parsed JSON may omit it
    if not from_json and impact.get("status") != "success":
        return {"status": "error", "message": "Could not compute operational impact"}
    if from_json and impact.get("status") == "error":
        return {"status": "error", "message": impact.get("message", "Could not compute operational impact")}

    lines = impact.get("affected_production_lines") or []
    delay_min = impact.get("estimated_delay_days_min", 5)
    delay_max = impact.get("estimated_delay_days_max", 15)
    delay_mid = (delay_min + delay_max) // 2
    customer_slas = profile.get("customer_slas") or []
    # Assume margin rate 30% for margin impact
    margin_rate = 0.30

    def _outcome(delay_days: int) -> dict:
        rev = sum((l.get("daily_revenue_usd") or 0) for l in lines if l.get("at_risk")) * delay_days
        sla = sum((s.get("penalty_per_day_usd") or 0) for s in customer_slas) * delay_days
        margin = rev * margin_rate
        return {
            "revenue_at_risk_usd": round(rev, 2),
            "sla_penalties_usd": round(sla, 2),
            "margin_impact_usd": round(margin, 2),
            "delay_days": delay_days,
        }

    best = _outcome(delay_min)
    expected = _outcome(delay_mid)
    worst = _outcome(delay_max)

    customers_affected = len(customer_slas)
    revenue_at_risk_usd = expected["revenue_at_risk_usd"]
    margin_impact_usd = expected["margin_impact_usd"]
    sla_penalties_usd = expected["sla_penalties_usd"]

    summary = (
        f"Revenue-at-risk: ${revenue_at_risk_usd / 1e6:.1f}M (expected). "
        f"Margin impact: ${margin_impact_usd / 1e6:.1f}M. "
        f"Customers affected: {customers_affected} major OEM accounts. "
        f"SLA penalty exposure: ${sla_penalties_usd / 1e3:.0f}K."
    )

    return {
        "status": "success",
        "revenue_at_risk_usd": revenue_at_risk_usd,
        "margin_impact_usd": margin_impact_usd,
        "sla_penalties_usd": sla_penalties_usd,
        "customers_affected": customers_affected,
        "best_case": best,
        "expected_case": expected,
        "worst_case": worst,
        "summary": summary,
    }
