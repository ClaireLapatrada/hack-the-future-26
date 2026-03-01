"""
Perception Tools — Signal ingestion and classification.
Used by the Perception Agent to monitor external disruption signals.

To switch to real APIs, see docs/PERCEPTION_APIS.md for which APIs to set up
(search, shipping, climate, supplier health) and suggested env vars.
"""

import os
import json
import re
from datetime import datetime
from pathlib import Path

# Load .env from project root, perception_agent, and orchestrator_agent so GOOGLE_SEARCH_*, NASA_API_KEY, GEMINI_API_KEY are available
try:
    from dotenv import load_dotenv
    _root = Path(__file__).resolve().parent.parent
    load_dotenv(_root / ".env")
    load_dotenv(_root / "perception_agent" / ".env")
    load_dotenv(_root / "orchestrator_agent" / ".env")
except ImportError:
    pass

import requests


def _call_google_custom_search(query: str, num: int = 10) -> dict | None:
    """Call Google Custom Search JSON API. Returns parsed JSON or None on failure."""
    api_key = os.getenv("GOOGLE_SEARCH_API_KEY") or os.getenv("GOOGLE_API_KEY")
    cx = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
    if not api_key or not cx:
        return None
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": api_key, "cx": cx, "q": query, "num": min(num, 10)}
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except (requests.RequestException, ValueError) as e:
        return {"error": str(e)}


def search_disruption_news(query: str) -> dict:
    """
    Search for supply chain disruption news related to a topic, region, or supplier.
    Requires GOOGLE_SEARCH_ENGINE_ID and either GOOGLE_SEARCH_API_KEY or GOOGLE_API_KEY.

    Args:
        query: Search query e.g. "Red Sea shipping disruption 2025"
    """
    data = _call_google_custom_search(query)
    if data is None:
        return {
            "status": "error",
            "query": query,
            "message": "Google Custom Search not configured. Set GOOGLE_SEARCH_ENGINE_ID and either GOOGLE_SEARCH_API_KEY or GOOGLE_API_KEY.",
            "signals": [],
            "scan_timestamp": datetime.now().isoformat(),
        }
    if "error" in data:
        return {
            "status": "error",
            "query": query,
            "message": data["error"],
            "signals": [],
            "scan_timestamp": datetime.now().isoformat(),
        }
    items = data.get("items") or []
    signals = []
    for it in items:
        snippet = it.get("snippet") or ""
        # Optional: extract date from pagemap if present
        published = datetime.now().isoformat()
        pagemap = it.get("pagemap") or {}
        meta = (pagemap.get("metatags") or [{}])[0]
        if isinstance(meta, dict):
            for date_key in ("article:published_time", "datePublished", "pubdate"):
                if meta.get(date_key):
                    published = meta[date_key]
                    break
        signals.append({
            "title": it.get("title") or "",
            "source": it.get("displayLink") or it.get("link", "")[:50],
            "published": published,
            "url": it.get("link") or "",
            "summary": snippet,
            "classified_type": None,
            "severity": None,
            "confidence_score": None,
        })
    return {
        "status": "success",
        "query": query,
        "articles_found": len(signals),
        "signals": signals,
        "scan_timestamp": datetime.now().isoformat(),
    }


def _load_active_disruption() -> dict:
    """Load config/active_disruption.json. When active is false, perception reports all operational."""
    root = Path(__file__).resolve().parent.parent
    path = root / "config" / "active_disruption.json"
    if not path.exists():
        return {"active": False, "shipping_lanes": {}}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"active": False, "shipping_lanes": {}}


def _operational_status() -> dict:
    """Default status when no disruption is active."""
    return {
        "status": "OPERATIONAL",
        "severity": "Low",
        "avg_delay_days": 0,
        "reroute_available": False,
        "reroute_via": None,
        "reroute_additional_days": 0,
        "carrier_surcharges_usd_per_teu": 0,
        "vessels_affected_pct": 0,
        "last_updated": datetime.now().isoformat(),
    }


def get_shipping_lane_status(lane: str) -> dict:
    """
    Get current operational status of a shipping lane.
    Reads config/active_disruption.json: when active is false, all lanes are OPERATIONAL
    until you run scripts/initiate_event.py to set a disruption.
    In production: wraps Project44 or Flexport API.

    Args:
        lane: Lane name e.g. "Asia-Europe (Suez)" or "Trans-Pacific"
    """
    state = _load_active_disruption()
    if not state.get("active"):
        status = _operational_status()
        return {"status": "success", "lane": lane, "lane_status": status}
    overrides = state.get("shipping_lanes") or {}
    if lane in overrides:
        status = dict(overrides[lane])
        status.setdefault("last_updated", datetime.now().isoformat())
        return {"status": "success", "lane": lane, "lane_status": status}
    status = _operational_status()
    return {"status": "success", "lane": lane, "lane_status": status}


# Approximate bounding boxes (min_lon, min_lat, max_lon, max_lat) for EONET region filter
_REGION_BBOX = {
    "Taiwan": (119.5, 21.5, 122.2, 25.5),
    "Vietnam": (102.0, 8.0, 110.0, 23.5),
    "Germany": (5.5, 47.0, 15.0, 55.5),
    "Poland": (14.0, 49.0, 24.5, 55.0),
    "Thailand": (97.0, 5.5, 106.0, 21.0),
    "South Korea": (124.5, 33.0, 132.0, 43.0),
    "Czech Republic": (12.0, 48.5, 19.0, 51.5),
}


def _point_in_bbox(lon: float, lat: float, bbox: tuple[float, float, float, float]) -> bool:
    min_lon, min_lat, max_lon, max_lat = bbox
    return min_lon <= lon <= max_lon and min_lat <= lat <= max_lat


def _event_in_region(event: dict, bbox: tuple[float, float, float, float]) -> bool:
    """Return True if any geometry of the event falls inside bbox."""
    geoms = event.get("geometry") or []
    for g in geoms:
        coords = g.get("coordinates")
        if not coords:
            continue
        # Point: [lon, lat]; Polygon: [[[lon, lat], ...]]
        if g.get("type") == "Point" and len(coords) >= 2:
            if _point_in_bbox(float(coords[0]), float(coords[1]), bbox):
                return True
        if g.get("type") == "Polygon" and coords and coords[0]:
            for ring in coords[:1]:  # exterior ring only
                for pt in ring:
                    if len(pt) >= 2 and _point_in_bbox(float(pt[0]), float(pt[1]), bbox):
                        return True
    return False


def _call_nasa_eonet(days: int = 30, limit: int = 100) -> dict | None:
    """Fetch open natural events from NASA EONET API v3. API key is optional (EONET may not use it)."""
    url = "https://eonet.gsfc.nasa.gov/api/v3/events"
    params = {"status": "open", "days": days, "limit": limit}
    api_key = os.getenv("NASA_API_KEY")
    if api_key:
        params["api_key"] = api_key
    try:
        r = requests.get(url, params=params, timeout=15)
        if not r.ok and api_key:
            # EONET may not accept api_key; retry without it
            params.pop("api_key", None)
            r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except (requests.RequestException, ValueError):
        return None


def get_climate_alerts(regions: list[str]) -> dict:
    """
    Fetch active climate and natural disaster alerts for given regions.
    Uses NASA EONET (Earth Observatory Natural Event Tracker) API.
    Set NASA_API_KEY in the environment (optional but recommended for higher rate limits).

    Args:
        regions: List of region names e.g. ["Taiwan", "Vietnam", "Germany"]
    """
    data = _call_nasa_eonet(days=30, limit=100)
    if data is None:
        return {
            "status": "error",
            "message": "Failed to fetch NASA EONET data.",
            "regions_checked": regions,
            "alerts": {r: {"active_alerts": []} for r in regions},
            "scan_timestamp": datetime.now().isoformat(),
        }
    events = data.get("events") or []
    results = {}
    for region in regions:
        bbox = _REGION_BBOX.get(region)
        if not bbox:
            results[region] = {"active_alerts": []}
            continue
        active_alerts = []
        for ev in events:
            if not _event_in_region(ev, bbox):
                continue
            title = ev.get("title") or "Unknown Event"
            categories = ev.get("categories") or []
            cat_title = categories[0].get("title", "Natural Event") if categories else "Natural Event"
            event_type = cat_title if isinstance(cat_title, str) else "Natural Event"
            geoms = ev.get("geometry") or []
            magnitude = None
            if geoms and geoms[0].get("magnitudeValue") is not None:
                try:
                    magnitude = float(geoms[0]["magnitudeValue"])
                except (TypeError, ValueError):
                    pass
            severity = "Medium"
            if magnitude is not None:
                severity = "High" if magnitude >= 60 else "Medium" if magnitude >= 35 else "Low"
            active_alerts.append({
                "type": event_type,
                "name": title[:80],
                "severity": severity,
                "affected_area": region,
                "expected_impact_days": None,
                "logistics_disruption_risk": "Medium" if severity in ("High", "Medium") else "Low",
                "eonet_id": ev.get("id"),
                "source": "NASA EONET",
            })
        results[region] = {"active_alerts": active_alerts}
    return {
        "status": "success",
        "regions_checked": regions,
        "alerts": results,
        "scan_timestamp": datetime.now().isoformat(),
    }


def _load_supplier_profile(supplier_id: str) -> dict | None:
    """Load supplier info from mock_profile.json (project root) or config/manufacturer_profile.json."""
    root = Path(__file__).resolve().parent.parent
    for path in [root / "mock_profile.json", root / "config" / "manufacturer_profile.json"]:
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                for s in data.get("suppliers") or []:
                    if s.get("id") == supplier_id:
                        return s
                return None
            except (json.JSONDecodeError, OSError):
                continue
    return None


def _call_gemini_supplier_health(supplier_id: str, supplier_info: dict | None) -> dict | None:
    """Ask Gemini to score supplier health. Returns health_data dict or None on failure."""
    try:
        from google import genai
    except ImportError:
        return None
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    client = genai.Client(api_key=api_key)
    name = (supplier_info or {}).get("name") or "Unknown"
    country = (supplier_info or {}).get("country") or "Unknown"
    category = (supplier_info or {}).get("category") or "Unknown"
    spend_pct = (supplier_info or {}).get("spend_pct")
    single_source = (supplier_info or {}).get("single_source", False)
    contract_end = (supplier_info or {}).get("contract_end") or "Unknown"
    prompt = f"""You are a supply chain risk analyst. Score this supplier's health for a manufacturer.

Supplier ID: {supplier_id}
Name: {name}
Country: {country}
Category: {category}
Spend % of total: {spend_pct}
Single source: {single_source}
Contract end: {contract_end}

Respond with ONLY a JSON object (no markdown, no explanation) with exactly these keys:
- overall_health_score (integer 0-100)
- financial_stability (one of: Strong, Moderate, Weak)
- payment_behavior (one of: Excellent, Good, Moderate, Poor)
- operational_reliability (one of: Excellent, Good, Moderate, Poor)
- geopolitical_risk_exposure (one of: Low, Medium, High, Critical)
- recent_flags (array of strings, or empty array)
- trend (one of: Stable, Declining, Rapidly Declining, Improving)
- recommendation (one short sentence)

Example format:
{{"overall_health_score": 72, "financial_stability": "Moderate", "payment_behavior": "Good", "operational_reliability": "Good", "geopolitical_risk_exposure": "High", "recent_flags": ["Elevated regional risk"], "trend": "Declining", "recommendation": "Monitor closely."}}
"""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        text = getattr(response, "text", None) or ""
        if not text:
            return None
        text = text.strip()
        # Strip markdown code block if present
        if "```" in text:
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```\s*$", "", text)
        data = json.loads(text)
        data["supplier_name"] = name
        return data
    except (Exception, json.JSONDecodeError):
        return None


def score_supplier_health(supplier_id: str) -> dict:
    """
    Score a supplier's financial and operational health using Gemini.
    Uses supplier context from mock_profile.json if present.
    Requires GEMINI_API_KEY (or GOOGLE_API_KEY) in the environment, or Vertex AI ADC.

    Args:
        supplier_id: Internal supplier ID e.g. "SUP-001"
    """
    state = _load_active_disruption()
    if not state.get("supplier_health_degraded", False):
        supplier_info = _load_supplier_profile(supplier_id)
        name = (supplier_info or {}).get("name") or "Unknown"
        return {
            "status": "success",
            "supplier_id": supplier_id,
            "health_data": {
                "supplier_name": name,
                "overall_health_score": 85,
                "financial_stability": "Strong",
                "payment_behavior": "Good",
                "operational_reliability": "Good",
                "geopolitical_risk_exposure": "Low",
                "recent_flags": [],
                "trend": "Stable",
                "recommendation": "No active disruption; monitoring as usual.",
            },
        }
    supplier_info = _load_supplier_profile(supplier_id)
    health_data = _call_gemini_supplier_health(supplier_id, supplier_info)
    if health_data is None:
        return {
            "status": "error",
            "supplier_id": supplier_id,
            "message": "Gemini API not available or returned invalid response. Set GEMINI_API_KEY or use Vertex AI.",
            "health_data": {
                "supplier_name": (supplier_info or {}).get("name") or "Unknown",
                "overall_health_score": None,
                "recommendation": "No data available",
            },
        }
    return {"status": "success", "supplier_id": supplier_id, "health_data": health_data}