"""
Memory Tools — Disruption log retrieval, pattern detection, and event logging.
Used by the Memory Agent. When QDRANT_URL and GEMINI_API_KEY are set, uses Qdrant
for semantic similarity search; otherwise uses keyword matching over JSON.
"""

import json
import os
import uuid
from pathlib import Path
from datetime import datetime

# Load .env so QDRANT_URL and GEMINI_API_KEY are available
try:
    from dotenv import load_dotenv
    _root = Path(__file__).resolve().parent.parent
    load_dotenv(_root / ".env")
    load_dotenv(_root / "memory_agent" / ".env")
except ImportError:
    pass

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PROJECT_ROOT = Path(__file__).resolve().parent.parent

QDRANT_COLLECTION = "disruption_events"
EMBEDDING_DIM = 768


def _history_path() -> Path:
    """Path to disruption history JSON (data/ or project root)."""
    for p in [DATA_DIR / "mock_disruption_history.json", PROJECT_ROOT / "mock_disruption_history.json"]:
        if p.exists():
            return p
    return DATA_DIR / "mock_disruption_history.json"


def _load_history() -> list:
    path = _history_path()
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def _embed_text(text: str) -> list[float] | None:
    """Embed text using Gemini. Returns None if embedding unavailable."""
    try:
        from google import genai
    except ImportError:
        return None
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    try:
        client = genai.Client(api_key=api_key)
        from google.genai import types as genai_types
        config = genai_types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM)
        result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=text[:8000],
            config=config,
        )
        if result and getattr(result, "embeddings", None) and len(result.embeddings) > 0:
            emb = result.embeddings[0]
            if getattr(emb, "values", None) is not None:
                return list(emb.values)
        return None
    except Exception:
        return None


def _qdrant_client():
    """Return Qdrant client if QDRANT_URL is set, else None."""
    url = os.getenv("QDRANT_URL", "").strip() or os.getenv("QDRANT_HOST")
    if not url:
        return None
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams
        if url.startswith("http"):
            client = QdrantClient(url=url, timeout=10)
        else:
            client = QdrantClient(host=url, port=6333, timeout=10)
        if not client.collection_exists(QDRANT_COLLECTION):
            client.create_collection(
                QDRANT_COLLECTION,
                vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
            )
        return client
    except Exception:
        return None


def _event_to_text(event: dict) -> str:
    """Build searchable text for embedding."""
    parts = [
        event.get("type", ""),
        event.get("region", ""),
        event.get("description", ""),
        event.get("lessons_learned", ""),
        (event.get("mitigation_taken") or {}).get("action", ""),
    ]
    return " ".join(str(p) for p in parts if p)


def _backfill_qdrant(client, history: list) -> None:
    """Backfill Qdrant from JSON history."""
    from qdrant_client.models import PointStruct
    for i, event in enumerate(history):
        text = _event_to_text(event)
        if not text:
            continue
        vec = _embed_text(text)
        if not vec:
            break
        point_id = event.get("event_id") or str(uuid.uuid4())
        try:
            client.upsert(
                QDRANT_COLLECTION,
                points=[PointStruct(id=point_id, vector=vec, payload=event)],
            )
        except Exception:
            pass


def retrieve_similar_disruptions(
    disruption_type: str,
    affected_region: str,
    top_k: int = 3
) -> dict:
    """
    Retrieve historically similar disruptions and their mitigation outcomes.
    Uses Qdrant semantic search when QDRANT_URL and GEMINI_API_KEY are set;
    otherwise uses keyword matching over JSON.

    Args:
        disruption_type: Type of disruption e.g. "Shipping Disruption", "Geopolitical"
        affected_region: Region affected e.g. "Red Sea", "Taiwan"
        top_k: Number of similar cases to return
    """
    client = _qdrant_client()
    query_text = f"{disruption_type} {affected_region}"
    if client:
        vec = _embed_text(query_text)
        if vec:
            try:
                res = client.count(QDRANT_COLLECTION)
                if res.count == 0:
                    _backfill_qdrant(client, _load_history())
                search = client.search(
                    collection_name=QDRANT_COLLECTION,
                    query_vector=vec,
                    limit=top_k,
                )
                top_cases = [hit.payload for hit in search if hit.payload]
                if top_cases:
                    insights = []
                    for case in top_cases:
                        insights.append({
                            "event_id": case.get("event_id"),
                            "date": case.get("date"),
                            "type": case.get("type"),
                            "description": case.get("description", ""),
                            "what_worked": (case.get("mitigation_taken") or {}).get("action", ""),
                            "outcome": (case.get("mitigation_taken") or {}).get("outcome", ""),
                            "cost_usd": (case.get("mitigation_taken") or {}).get("cost_usd"),
                            "actual_loss_usd": (case.get("impact") or {}).get("actual_revenue_lost_usd"),
                            "lesson": case.get("lessons_learned", ""),
                        })
                    summary = (
                        f"Found {len(insights)} similar past disruption(s). "
                        f"Most recent: {insights[0]['date']} — '{insights[0]['what_worked']}' "
                        f"resulted in: {insights[0]['outcome']}."
                    )
                    return {
                        "status": "success",
                        "query": {"type": disruption_type, "region": affected_region},
                        "similar_cases_found": len(insights),
                        "cases": insights,
                        "summary": summary,
                        "source": "qdrant",
                    }
            except Exception:
                pass
    # Fallback: keyword match over JSON
    history = _load_history()

    # Simple keyword match (in production: vector embedding similarity)
    def relevance_score(event: dict) -> int:
        score = 0
        if event.get("type", "").lower() == disruption_type.lower():
            score += 3
        if affected_region.lower() in event.get("region", "").lower():
            score += 3
        if affected_region.lower() in event.get("description", "").lower():
            score += 2
        if disruption_type.lower() in event.get("description", "").lower():
            score += 1
        return score

    scored = [(e, relevance_score(e)) for e in history]
    scored.sort(key=lambda x: x[1], reverse=True)
    top_cases = [e for e, s in scored[:top_k] if s > 0]

    insights = []
    for case in top_cases:
        insights.append({
            "event_id": case["event_id"],
            "date": case["date"],
            "type": case["type"],
            "description": case["description"],
            "what_worked": case["mitigation_taken"]["action"],
            "outcome": case["mitigation_taken"]["outcome"],
            "cost_usd": case["mitigation_taken"]["cost_usd"],
            "actual_loss_usd": case["impact"]["actual_revenue_lost_usd"],
            "lesson": case["lessons_learned"]
        })

    summary = ""
    if insights:
        summary = (
            f"Found {len(insights)} similar past disruption(s). "
            f"Most recent: {insights[0]['date']} — '{insights[0]['what_worked']}' "
            f"resulted in: {insights[0]['outcome']}."
        )
    else:
        summary = "No closely matching historical disruptions found. Proceeding without precedent."

    return {
        "status": "success",
        "query": {"type": disruption_type, "region": affected_region},
        "similar_cases_found": len(insights),
        "cases": insights,
        "summary": summary
    }


def log_disruption_event(
    event_type: str,
    region: str,
    severity: str,
    affected_suppliers: list[str],
    description: str,
    mitigation_action: str,
    estimated_cost_usd: float,
    outcome: str = "Pending"
) -> dict:
    """
    Log a new disruption event to persistent memory for future learning.
    In production: writes to Firestore and triggers embedding update in Vector Search.

    Args:
        event_type: Type of disruption
        region: Affected region
        severity: Severity level
        affected_suppliers: List of supplier IDs
        description: Disruption description
        mitigation_action: Action taken
        estimated_cost_usd: Cost of mitigation
        outcome: Result (Pending / Success / Partial / Failed)
    """
    event_id = f"EVT-{datetime.now().strftime('%Y-%m%d')}-{len(_load_history()) + 1:03d}"

    new_event = {
        "event_id": event_id,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "type": event_type,
        "region": region,
        "severity": severity,
        "affected_suppliers": affected_suppliers,
        "description": description,
        "impact": {
            "delay_days": None,  # To be updated when outcome known
            "revenue_at_risk_usd": None,
            "actual_revenue_lost_usd": None
        },
        "mitigation_taken": {
            "action": mitigation_action,
            "cost_usd": estimated_cost_usd,
            "outcome": outcome
        },
        "lessons_learned": "To be determined based on outcome.",
        "logged_by": "Supply Chain Resilience Agent",
        "logged_at": datetime.now().isoformat()
    }

    # For demo: append to local JSON file; optionally index in Qdrant
    write_status = "written_to_local_json"
    try:
        history = _load_history()
        history.append(new_event)
        path = _history_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        write_status = f"write_failed: {str(e)}"
    # Upsert to Qdrant when available
    qclient = _qdrant_client()
    if qclient:
        text = _event_to_text(new_event)
        vec = _embed_text(text) if text else None
        if vec:
            try:
                from qdrant_client.models import PointStruct
                qclient.upsert(
                    QDRANT_COLLECTION,
                    points=[PointStruct(id=event_id, vector=vec, payload=new_event)],
                )
                write_status = "written_to_local_json_and_qdrant"
            except Exception:
                pass

    return {
        "status": "success",
        "event_id": event_id,
        "logged_event": new_event,
        "storage_status": write_status,
        "note": "When QDRANT_URL and GEMINI_API_KEY are set, events are also indexed in Qdrant for semantic search."
    }


def get_recurring_risk_patterns() -> dict:
    """
    Analyze disruption history to identify recurring risk patterns.
    Used to proactively warn about predictable future risks.
    """
    history = _load_history()

    # Frequency analysis
    type_counts = {}
    supplier_counts = {}
    region_counts = {}
    total_actual_loss = 0
    total_mitigation_cost = 0

    for event in history:
        t = event.get("type", "Unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

        for sup in event.get("affected_suppliers", []):
            supplier_counts[sup] = supplier_counts.get(sup, 0) + 1

        region = event.get("region", "Unknown")
        region_counts[region] = region_counts.get(region, 0) + 1

        total_actual_loss += event.get("impact", {}).get("actual_revenue_lost_usd", 0) or 0
        total_mitigation_cost += event.get("mitigation_taken", {}).get("cost_usd", 0) or 0

    # Identify highest risk supplier
    most_affected_supplier = max(supplier_counts, key=supplier_counts.get) if supplier_counts else None
    most_common_type = max(type_counts, key=type_counts.get) if type_counts else None
    most_affected_region = max(region_counts, key=region_counts.get) if region_counts else None

    patterns = []
    if most_affected_supplier and supplier_counts.get(most_affected_supplier, 0) >= 2:
        patterns.append({
            "pattern": "Recurring Supplier Risk",
            "detail": f"{most_affected_supplier} has been affected in {supplier_counts[most_affected_supplier]} disruptions",
            "recommendation": f"Prioritize backup qualification for {most_affected_supplier}"
        })
    if most_common_type and type_counts.get(most_common_type, 0) >= 2:
        patterns.append({
            "pattern": "Recurring Disruption Type",
            "detail": f"'{most_common_type}' has occurred {type_counts[most_common_type]} times",
            "recommendation": f"Develop standing playbook for {most_common_type} events"
        })
    if most_affected_region and region_counts.get(most_affected_region, 0) >= 2:
        patterns.append({
            "pattern": "High-Risk Region",
            "detail": f"{most_affected_region} appears in {region_counts[most_affected_region]} disruptions",
            "recommendation": f"Reduce single-region dependency for {most_affected_region}"
        })

    return {
        "status": "success",
        "total_events_analyzed": len(history),
        "total_historical_losses_usd": total_actual_loss,
        "total_mitigation_costs_usd": total_mitigation_cost,
        "disruption_by_type": type_counts,
        "disruption_by_region": region_counts,
        "most_affected_suppliers": supplier_counts,
        "recurring_patterns": patterns,
        "summary": f"Analyzed {len(history)} historical events. "
                   f"Total losses: ${total_actual_loss:,.0f}. "
                   f"{len(patterns)} recurring pattern(s) identified."
    }