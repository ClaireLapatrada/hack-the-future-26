"""
Action Tools — Generate and execute operational actions.
Used by the Action Execution Agent.

Includes: supplier emails, Slack alerts, ERP/PO adjustments, approval inbox,
purchase order adjustment suggestions (restock suggestions + execute after approval),
escalation triggers (decision transparency), workflow integrations and client context.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
PENDING_APPROVALS_PATH = PROJECT_ROOT / "data" / "pending_approvals.json"
ESCALATIONS_PATH = PROJECT_ROOT / "data" / "escalations.json"

def _load_action_config() -> dict:
    path = Path(os.getenv("ACTION_CONFIG_PATH", CONFIG_DIR / "action_config.json"))
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def draft_supplier_email(
    supplier_name: str,
    supplier_contact: str,
    disruption_context: str,
    ask: str,
    sender_name: str = "Supply Chain Operations Team",
    company_name: str = "AutomotiveParts GmbH"
) -> dict:
    """
    Draft a professional supplier outreach email based on disruption context.
    In production: integrates with Gmail API to send or save as draft.

    Args:
        supplier_name: Name of supplier e.g. "SemiTech Asia"
        supplier_contact: Email contact at supplier
        disruption_context: What disruption is occurring
        ask: What you need from the supplier (expedite, confirm, reroute, etc.)
        sender_name: Name of person/team sending
        company_name: Your company name
    """
    timestamp = datetime.now().strftime("%B %d, %Y")

    email_body = f"""Subject: URGENT: Supply Continuity Request — {disruption_context[:50]}

Dear {supplier_name} Team,

I am reaching out on behalf of {company_name} regarding a developing situation that may impact our supply continuity.

**Situation:**
{disruption_context}

**Our Request:**
{ask}

Given our production commitments to key OEM customers (BMW Group, Volkswagen AG), maintaining supply continuity is critical. We have active production lines that are dependent on your components, and any delay beyond our current safety stock window will result in line stoppages.

We would appreciate your urgent response on the following:
1. Current status of our open purchase orders
2. Your assessment of timeline impact
3. Available options to expedite, reroute, or partially fulfill our order

We are prepared to discuss cost-sharing arrangements if alternative logistics options are required.

Please respond to this message at your earliest convenience, or contact our procurement team directly at procurement@automotiveparts.de or +49 711 XXX-XXXX.

Thank you for your partnership and prompt attention to this matter.

Best regards,
{sender_name}
{company_name}
Supply Chain Risk Management
{timestamp}

---
This communication was flagged as URGENT by our supply chain risk monitoring system.
Reference: SCR-{datetime.now().strftime('%Y%m%d-%H%M')}
"""

    return {
        "status": "success",
        "draft_email": {
            "to": supplier_contact,
            "subject": f"URGENT: Supply Continuity Request — {disruption_context[:50]}",
            "body": email_body,
            "priority": "High",
            "draft_timestamp": datetime.now().isoformat()
        },
        "next_step": "Review draft and approve to send via Gmail API",
        "auto_send_eligible": False,  # Always human-approved for supplier comms
        "reference_id": f"SCR-{datetime.now().strftime('%Y%m%d-%H%M')}"
    }


def send_slack_alert(
    channel: str,
    severity: str,
    disruption_summary: str,
    recommended_action: str,
    financial_exposure_usd: float,
    requires_approval: bool = True
) -> dict:
    """
    Send a Slack escalation alert to operations or executive channel.
    In production: wraps Slack Web API (chat.postMessage).

    Args:
        channel: Slack channel e.g. "#supply-chain-alerts" or "#executive-ops"
        severity: "LOW", "MEDIUM", "HIGH", "CRITICAL"
        disruption_summary: Brief description of the disruption
        recommended_action: What the agent recommends
        financial_exposure_usd: Dollar exposure
        requires_approval: Whether human approval is needed before action
    """
    severity_emoji = {
        "LOW": "🟡",
        "MEDIUM": "🟠",
        "HIGH": "🔴",
        "CRITICAL": "🚨"
    }.get(severity, "⚪")

    message_blocks = [
        {
            "type": "header",
            "text": f"{severity_emoji} Supply Chain Alert — {severity} Severity"
        },
        {
            "type": "section",
            "text": f"*Disruption:* {disruption_summary}"
        },
        {
            "type": "section",
            "text": f"*Financial Exposure:* ${financial_exposure_usd:,.0f}"
        },
        {
            "type": "section",
            "text": f"*Recommended Action:* {recommended_action}"
        },
        {
            "type": "section",
            "text": f"*Requires Approval:* {'✅ Yes — awaiting authorization' if requires_approval else '⚡ Auto-executed'}"
        },
        {
            "type": "context",
            "text": f"Generated by Supply Chain Resilience Agent • {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}"
        }
    ]

    # In production: requests.post("https://slack.com/api/chat.postMessage", ...)
    return {
        "status": "success",
        "channel": channel,
        "severity": severity,
        "message_preview": f"{severity_emoji} [{severity}] {disruption_summary} | Exposure: ${financial_exposure_usd:,.0f}",
        "blocks": message_blocks,
        "sent_at": datetime.now().isoformat(),
        "mock_note": "In production: delivered via Slack Web API"
    }


def flag_erp_reorder_adjustment(
    item_id: str,
    adjustment_type: str,
    new_quantity: int,
    reason: str,
    auto_execute: bool = False
) -> dict:
    """
    Flag or execute a purchase order / reorder point adjustment in the ERP.
    In production: wraps SAP or Oracle ERP REST API.

    Args:
        item_id: ERP item ID e.g. "SEMI-MCU-32"
        adjustment_type: "increase_reorder_point", "emergency_po", "increase_buffer",
                         "pause_po", "expedite_po"
        new_quantity: New quantity value
        reason: Reason for adjustment (used in ERP change log)
        auto_execute: If True, auto-submits. If False, creates pending approval.
    """
    adjustment_descriptions = {
        "increase_reorder_point": f"Reorder point raised to {new_quantity} units",
        "emergency_po": f"Emergency purchase order created for {new_quantity} units",
        "increase_buffer": f"Safety stock target increased to {new_quantity} units",
        "pause_po": f"Open PO paused — {new_quantity} units on hold",
        "expedite_po": f"Expedite flag set on existing PO — priority: {new_quantity}"
    }

    erp_change_record = {
        "change_id": f"ERP-CHG-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "item_id": item_id,
        "adjustment_type": adjustment_type,
        "description": adjustment_descriptions.get(adjustment_type, f"Adjustment: {adjustment_type}"),
        "quantity": new_quantity,
        "reason": reason,
        "status": "EXECUTED" if auto_execute else "PENDING_APPROVAL",
        "created_at": datetime.now().isoformat(),
        "created_by": "Supply Chain Resilience Agent",
        "approval_required": not auto_execute
    }

    return {
        "status": "success",
        "erp_change": erp_change_record,
        "next_step": "Auto-executed in ERP" if auto_execute else "Awaiting procurement manager approval",
        "mock_note": "In production: submitted via SAP REST API or Oracle Fusion"
    }


def get_po_adjustment_suggestions() -> dict:
    """
    Monitor inventory levels and suggest order restocks for human approval (or auto-execute if under threshold).
    Reads ERP inventory and compares to reorder/target buffer from config.
    """
    config = _load_action_config()
    po_cfg = config.get("po_adjustment", {})
    threshold_usd = po_cfg.get("auto_restock_threshold_usd", 15000)
    reorder_days = po_cfg.get("reorder_threshold_days", 10)
    target_days = po_cfg.get("target_buffer_days", 30)
    max_auto_qty = po_cfg.get("max_auto_restock_quantity_per_line", 2000)

    erp_path = Path(os.getenv("ERP_JSON_PATH", str(DATA_DIR / "mock_erp.json")))
    if not erp_path.exists():
        return {"status": "error", "message": "ERP data not found", "suggestions": []}
    with open(erp_path, encoding="utf-8") as f:
        erp = json.load(f)
    inventory = erp.get("inventory") or []
    unit_cost_map = {"SEMI-MCU-32": 12.5, "SEMI-SENSOR-01": 8.0, "STEEL-BRK-07": 17.0, "STEEL-FRAME-02": 22.0}

    suggestions = []
    for item in inventory:
        item_id = item.get("item_id", "")
        days_on_hand = item.get("days_on_hand") or 0
        daily_consumption = item.get("daily_consumption") or 1
        on_order = item.get("on_order_units") or 0
        if days_on_hand >= target_days:
            continue
        if days_on_hand >= reorder_days and on_order > 0:
            continue
        shortfall_days = max(0, target_days - days_on_hand)
        suggested_qty = min(int(daily_consumption * shortfall_days), int(daily_consumption * (target_days + 14)))
        if suggested_qty <= 0:
            suggested_qty = int(daily_consumption * 14)
        unit_cost = unit_cost_map.get(item_id, 12.0)
        estimated_cost_usd = suggested_qty * unit_cost
        auto_eligible = estimated_cost_usd <= threshold_usd and suggested_qty <= max_auto_qty
        reason = f"Days on hand ({days_on_hand}d) below reorder ({reorder_days}d); target buffer {target_days}d."
        suggestions.append({
            "item_id": item_id,
            "description": item.get("description", item_id),
            "suggested_quantity": suggested_qty,
            "reason": reason,
            "estimated_cost_usd": round(estimated_cost_usd, 2),
            "auto_eligible": auto_eligible,
            "days_on_hand": days_on_hand,
            "target_buffer_days": target_days,
        })

    return {
        "status": "success",
        "suggestions": suggestions,
        "auto_restock_threshold_usd": threshold_usd,
        "summary": f"Found {len(suggestions)} restock suggestion(s). {sum(1 for s in suggestions if s['auto_eligible'])} eligible for auto-execute (under ${threshold_usd:,}).",
    }


def submit_restock_for_approval(
    item_id: str,
    suggested_quantity: int,
    reason: str,
    estimated_cost_usd: float,
    title: str = "",
) -> dict:
    """Submit a restock suggestion for human approval. After approval, call execute_approved_restock(approval_id)."""
    approval_id = f"RST-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    entry = {
        "id": approval_id,
        "type": "restock",
        "severity": "HIGH" if estimated_cost_usd > 50000 else "MEDIUM",
        "title": title or f"Restock: {item_id} — {suggested_quantity} units",
        "situation": reason,
        "recommendation": f"APPROVE — Restock {item_id} for {suggested_quantity} units (est. ${estimated_cost_usd:,.0f}).",
        "confidence": "90%",
        "auditLog": [{"time": "—", "text": reason}, {"time": "—", "text": f"Estimated cost: ${estimated_cost_usd:,.0f}"}],
        "status": "pending",
        "createdAt": datetime.now().isoformat(),
        "item_id": item_id,
        "suggested_quantity": suggested_quantity,
        "estimated_cost_usd": estimated_cost_usd,
        "adjustment_reason": reason,
    }
    PENDING_APPROVALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        if PENDING_APPROVALS_PATH.exists():
            with open(PENDING_APPROVALS_PATH, encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = []
        items = data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        items = []
    items.append(entry)
    with open(PENDING_APPROVALS_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)
    return {"status": "success", "approval_id": approval_id, "message": "Restock submitted for approval.", "next_step": "Call execute_approved_restock(approval_id) after human approval."}


def execute_approved_restock(approval_id: str) -> dict:
    """Execute a restock after human approval. Reads approval (type=restock, status=approved), then creates PO with auto_execute=True."""
    if not PENDING_APPROVALS_PATH.exists():
        return {"status": "error", "message": "No approvals file found"}
    try:
        with open(PENDING_APPROVALS_PATH, encoding="utf-8") as f:
            items = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"status": "error", "message": "Could not read approvals file"}
    items = items if isinstance(items, list) else []
    entry = next((e for e in items if e.get("id") == approval_id), None)
    if not entry:
        return {"status": "error", "message": f"Approval {approval_id} not found"}
    if entry.get("type") != "restock":
        return {"status": "error", "message": f"Approval {approval_id} is not a restock"}
    if entry.get("status") != "approved":
        return {"status": "error", "message": f"Approval {approval_id} not approved (status={entry.get('status')})"}
    item_id = entry.get("item_id", "")
    qty = entry.get("suggested_quantity", 0)
    reason = entry.get("adjustment_reason", "Approved restock")
    result = flag_erp_reorder_adjustment(item_id=item_id, adjustment_type="emergency_po", new_quantity=qty, reason=reason, auto_execute=True)
    for e in items:
        if e.get("id") == approval_id:
            e["status"] = "executed"
            e["executed_at"] = datetime.now().isoformat()
            break
    with open(PENDING_APPROVALS_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)
    return {"status": "success", "approval_id": approval_id, "erp_result": result, "message": f"Restock executed: {item_id} — {qty} units."}


def escalate_to_management(
    trigger_reason: str,
    severity: str,
    problem_summary: str,
    decision_transparency_json: str = "{}",
    suggested_recipients: str = "VP Operations, CFO",
) -> dict:
    """
    Escalate a problem to higher management. Include decision_transparency fields:
    what was detected, what the agent decided, why, what requires human decision.
    See action_config.json escalation_triggers and decision_transparency.
    """
    config = _load_action_config()
    transparency_cfg = config.get("decision_transparency", {}).get("include_in_escalation", [])
    try:
        transparency = json.loads(decision_transparency_json) if decision_transparency_json else {}
    except json.JSONDecodeError:
        transparency = {}
    escalation_id = f"ESC-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    record = {
        "id": escalation_id,
        "trigger_reason": trigger_reason,
        "severity": severity.upper(),
        "problem_summary": problem_summary,
        "suggested_recipients": suggested_recipients,
        "decision_transparency": {k: transparency.get(k, "—") for k in transparency_cfg} if transparency_cfg else transparency,
        "created_at": datetime.now().isoformat(),
        "status": "pending_review",
    }
    ESCALATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(ESCALATIONS_PATH, encoding="utf-8") as f:
            escalations = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        escalations = []
    if not isinstance(escalations, list):
        escalations = []
    escalations.append(record)
    with open(ESCALATIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(escalations, f, indent=2)
    return {"status": "success", "escalation_id": escalation_id, "trigger_reason": trigger_reason, "suggested_recipients": suggested_recipients, "message": "Escalation created for higher management."}


def get_client_context() -> dict:
    """Return client company stance, sustainability goals, financial constraints, legal, SCM inputs for mitigation decisions."""
    config = _load_action_config()
    ctx = config.get("client_context", {})
    return {"status": "success", "client_context": ctx, "summary": "Company stance, sustainability, financial, legal, and SCM inputs."}


def get_workflow_integration_status() -> dict:
    """Return status of integrations with client supply chain software (ERP, Slack, email, WMS, TMS) for one-stop UI."""
    config = _load_action_config()
    integrations = config.get("workflow_integrations", {})
    connected = [k for k, v in (integrations.items() if isinstance(integrations, dict) else []) if isinstance(v, dict) and v.get("connected")]
    return {
        "status": "success",
        "integrations": integrations,
        "connected_systems": connected,
        "one_stop_ui_summary": "All supply chain mitigation actions—alerts, restock suggestions, approvals, escalations—available in one place. Add WMS/TMS via config for full view.",
    }


def submit_mitigation_for_approval(
    title: str,
    recommendation: str,
    situation: str,
    severity: str = "HIGH",
    context_summary: str = "",
    scenario_name: str = "",
    incremental_cost_usd: float = 0.0,
) -> dict:
    """
    Submit a mitigation recommendation for human approval. When the agent has
    run planning (e.g. rank_scenarios) and identified a mitigation that requires
    sign-off (e.g. airfreight > $50K, ERP change, supplier email), call this to
    add it to the approval inbox so the user can accept or reject in the UI.

    Args:
        title: Short title e.g. "Emergency Airfreight — SEMI-MCU-32"
        recommendation: Agent recommendation text e.g. "APPROVE — Emergency Airfreight for 1,600 units"
        situation: Description of the situation and impact
        severity: "LOW", "MEDIUM", "HIGH", "CRITICAL"
        context_summary: Optional brief context from risk/perception
        scenario_name: Optional name from planning e.g. "Emergency Airfreight"
        incremental_cost_usd: Optional cost from scenario financials
    """
    approval_id = f"APPR-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    severity_normalized = severity.upper() if severity else "HIGH"
    if severity_normalized not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
        severity_normalized = "HIGH"

    audit_log = []
    if context_summary:
        audit_log.append({"time": "—", "text": context_summary})
    if scenario_name or incremental_cost_usd:
        cost_str = f"${incremental_cost_usd:,.0f}" if incremental_cost_usd else ""
        audit_log.append({"time": "—", "text": f"Scenario: {scenario_name or 'Mitigation'}. {cost_str}".strip()})
    audit_log.append({"time": "—", "text": recommendation})
    if not audit_log:
        audit_log.append({"time": "—", "text": recommendation})

    entry = {
        "id": approval_id,
        "severity": severity_normalized,
        "title": title,
        "situation": situation,
        "recommendation": recommendation,
        "confidence": "90%",
        "auditLog": audit_log,
        "status": "pending",
        "createdAt": datetime.now().isoformat(),
    }

    PENDING_APPROVALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        if PENDING_APPROVALS_PATH.exists():
            with open(PENDING_APPROVALS_PATH, encoding="utf-8") as f:
                data = json.load(f)
            items = data if isinstance(data, list) else []
        else:
            items = []
    except (json.JSONDecodeError, OSError):
        items = []
    items.append(entry)
    with open(PENDING_APPROVALS_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)

    return {
        "status": "success",
        "approval_id": approval_id,
        "message": "Mitigation submitted for human approval; visible in Approval Inbox.",
        "next_step": "User can approve or reject at /approvals",
    }


def generate_executive_summary(
    disruption_event_json: str,
    risk_assessment_json: str,
    recommended_scenario_json: str,
    actions_taken_json: str
) -> dict:
    """
    Generate a formatted executive summary document for leadership escalation.

    Args:
        disruption_event_json: JSON object with signal data from perception agent (e.g. description, severity, affected_regions)
        risk_assessment_json: JSON object with risk data including total_financial_exposure_usd, total_revenue_at_risk_usd, sla_penalties_at_risk_usd, disruption_duration_days, affected_production_lines
        recommended_scenario_json: JSON object with top-ranked scenario (scenario_name, description, financials.incremental_cost_usd, service_level_protection, timing.implementation_days)
        actions_taken_json: JSON array of action objects (each with description or summary)
    """
    try:
        disruption_event = json.loads(disruption_event_json)
        risk_assessment = json.loads(risk_assessment_json)
        recommended_scenario = json.loads(recommended_scenario_json)
        actions_taken = json.loads(actions_taken_json)
    except (TypeError, json.JSONDecodeError):
        return {"status": "error", "message": "All arguments must be valid JSON strings"}
    if not isinstance(actions_taken, list):
        actions_taken = [actions_taken]
    timestamp = datetime.now().strftime("%B %d, %Y at %H:%M UTC")

    summary_text = f"""
═══════════════════════════════════════════════════════════════
SUPPLY CHAIN RISK EXECUTIVE BRIEF
Generated: {timestamp}
Classification: INTERNAL — OPERATIONS SENSITIVE
═══════════════════════════════════════════════════════════════

SITUATION
─────────
{disruption_event.get('description', 'N/A')}
Severity: {disruption_event.get('severity', 'Unknown')}
Regions Affected: {', '.join(disruption_event.get('affected_regions') or []) if isinstance(disruption_event.get('affected_regions'), list) else str(disruption_event.get('affected_regions', 'N/A'))}

OPERATIONAL IMPACT
──────────────────
• Total Financial Exposure: ${risk_assessment.get('total_financial_exposure_usd', 0):,.0f}
  - Revenue at Risk: ${risk_assessment.get('total_revenue_at_risk_usd', 0):,.0f}
  - SLA Penalties at Risk: ${risk_assessment.get('sla_penalties_at_risk_usd', 0):,.0f}
• Disruption Duration Estimate: {risk_assessment.get('disruption_duration_days', 'TBD')} days
• Production Lines Affected: {len(risk_assessment.get('affected_production_lines', []))}

RECOMMENDED MITIGATION
───────────────────────
Strategy: {recommended_scenario.get('scenario_name', 'N/A')}
Description: {recommended_scenario.get('description', 'N/A')}
Incremental Cost: ${recommended_scenario.get('financials', {}).get('incremental_cost_usd', 0):,.0f}
Service Level Protection: {recommended_scenario.get('service_level_protection', 'N/A')}
Implementation Time: {recommended_scenario.get('timing', {}).get('implementation_days', 'N/A')} days

ACTIONS INITIATED
─────────────────
{chr(10).join(f"• {a.get('description', str(a))}" for a in actions_taken) or "• No actions taken yet"}

DECISION REQUIRED
─────────────────
Please authorize the recommended mitigation strategy within 4 hours to prevent
production line stoppage. Agent is standing by for executive approval.

Contact: AI Operations Co-Pilot | supply-chain-agent@automotiveparts.de
═══════════════════════════════════════════════════════════════
"""

    return {
        "status": "success",
        "summary": summary_text,
        "generated_at": datetime.now().isoformat(),
        "severity": disruption_event.get("severity", "Unknown"),
        "financial_exposure_usd": risk_assessment.get("total_financial_exposure_usd", 0),
        "decision_deadline_hours": 4
    }
