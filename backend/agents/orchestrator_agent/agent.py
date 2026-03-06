"""
Root Orchestrator Agent — Sub-agent architecture (AgentTool).

The orchestrator delegates to five sub-agents (or a subset for 429 diagnosis).
Set ORCHESTRATOR_SUBAGENTS=perception or perception,memory etc. to enable sub-agents one by one;
leave unset or set to "all" for all five. Use "" for none (orchestrator + breather only).
"""

import os
import time
from google.adk.agents import Agent
from backend.tools.delayed_agent_tool import DelayedAgentTool

# Sub-agents (must have project root on sys.path when this module loads)
from backend.agents.perception_agent.agent import perception_agent
from backend.agents.memory_agent.agent import memory_agent
from backend.agents.risk_agent.agent import risk_agent
from backend.agents.planning_agent.agent import planning_agent
from backend.agents.action_agent.agent import action_agent

# Order and mapping for ORCHESTRATOR_SUBAGENTS (e.g. "perception" or "perception,memory")
SUBAGENT_ORDER = ["perception", "memory", "risk", "planning", "action"]
SUBAGENT_AGENTS = {
    "perception": perception_agent,
    "memory": memory_agent,
    "risk": risk_agent,
    "planning": planning_agent,
    "action": action_agent,
}


def _enabled_subagents() -> list[str]:
    """Parse ORCHESTRATOR_SUBAGENTS. Empty or 'none' = []; 'all' or unset = all; else comma-separated names."""
    raw = (os.environ.get("ORCHESTRATOR_SUBAGENTS") or "all").strip().lower()
    if raw in ("", "none", "0"):
        return []
    if raw == "all":
        return list(SUBAGENT_ORDER)
    return [n.strip() for n in raw.split(",") if n.strip() and n.strip() in SUBAGENT_AGENTS]


def rate_limit_breather(message: str = "ready") -> dict:
    """Call before/between sub-agents. Uses same SUBAGENT_BREATHER_SECONDS as DelayedAgentTool."""
    delay = int(os.environ.get("SUBAGENT_BREATHER_SECONDS", "10"))
    delay = max(0, min(120, delay))
    if delay > 0:
        time.sleep(delay)
    return {"status": "ok", "message": message, "waited_seconds": delay}


def _full_pipeline_instruction(profile: str) -> str:
    """Full pipeline (same detail as flat agent) when all five sub-agents are enabled."""
    return """You are an Autonomous Supply Chain Resilience Agent — an intelligent operations co-pilot for AutomotiveParts GmbH.

**RATE LIMIT:** Before ANY sub-agent, call rate_limit_breather(message="ready"). After EACH sub-agent returns, call rate_limit_breather(message="next") before the next.
""" + profile + """
PIPELINE — call each agent in order:

STEP 0 — RATE LIMIT: Call rate_limit_breather(message="ready"). Wait for response.

STEP 1 — PERCEIVE: Call perception_agent with: "Run full disruption scan: search_disruption_news('global supply chain disruptions'), get_shipping_lane_status for Asia-Europe (Suez), Asia-Europe (Air), Intra-Europe (Road), get_climate_alerts for Taiwan, Vietnam, Poland, Germany, score_supplier_health for SUP-001 and SUP-003. Return structured summary with threat level (LOW/MEDIUM/HIGH/CRITICAL), which signals need escalation, timestamp. If news/climate APIs error, continue with lane status and supplier health." Then rate_limit_breather(message="next").

STEP 2 — MEMORY: Call memory_learning_agent with: "Retrieve similar past disruptions and recurring risk patterns. Use disruption type and region from perception. Return Memory Brief: historical case, what worked/didn't, patterns, mitigation cost range." Then rate_limit_breather(message="next").

STEP 3 — RISK (only if HIGH/CRITICAL): Call risk_intelligence_agent with: "Use perception and memory. get_disruption_probability SUP-001 and SUP-003 (30d), get_supplier_exposure(SUP-001), get_inventory_runway(SEMI-MCU-32), calculate_revenue_at_risk(SUP-001, estimated_delay_days), calculate_sla_breach_probability for BMW Group and Volkswagen AG. Return risk assessment: severity, exposure, runway, SLA probability, urgency." Then rate_limit_breather(message="next").

STEP 4 — PLAN (only if HIGH/CRITICAL): Call scenario_planning_agent with: "Simulate mitigation scenarios for SEMI-MCU-32: airfreight, buffer_build, alternate_supplier. run_scenario_simulation or evaluate_mitigation_tradeoffs risk_appetite='low'. Airfreight Taiwan→Germany if relevant. rank_scenarios, create_planning_document. If cost > $50K call submit_mitigation_for_approval. Return top scenario, cost, any approval." Then rate_limit_breather(message="next").

STEP 5 — ACTION: Call action_execution_agent with: "get_po_adjustment_suggestions, submit_restock_for_approval where needed; send_slack_alert #supply-chain-alerts; draft_supplier_email if needed (do not send); flag_erp_reorder_adjustment; if exposure > $500K or CRITICAL or SLA > 70% escalate_to_management; if exposure > $500K generate_executive_summary. Return actions (AUTO vs PENDING)." Then rate_limit_breather(message="next").

STEP 6 — LOG: Call memory_learning_agent with: "Log disruption event: type, region, severity, suppliers, description, mitigation_action, estimated_cost_usd, outcome=Pending. Confirm logged."

THRESHOLDS: Escalate CEO/CFO if > $1M; VP Ops if > $500K. < 5 days inventory = CRITICAL. SLA breach > 70% = C-suite. Supplier emails = draft only. Slack = always send.

END EVERY RUN WITH:
═══ SUPPLY CHAIN OPERATIONS BRIEFING ═══
Timestamp | Threat Level (from perception) | Signals: N found • details
Financial Exposure | Inventory Runway (days, item)
Disruption probability 30d (supplier, %, classification)
Top Recommendation | Cost | Time
Actions: ✅ auto-done | ⏳ pending
Reasoning: 2-3 sentences
═══════════════════════════════════════
"""


def _build_instruction(enabled: list[str]) -> str:
    """Build instruction: full detail when all five sub-agents enabled, else abbreviated for subset."""
    profile = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANUFACTURER PROFILE (context only — do NOT use for threat/lane status):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Company: AutomotiveParts GmbH | Revenue: $180M/year
Key supplier: SUP-001 SemiTech Asia (Taiwan) — 42% spend, single source for some parts
Customers: BMW Group ($50K/day penalty), Volkswagen AG ($35K/day penalty)
Risk appetite: LOW — service level protection is top priority
Critical item: SEMI-MCU-32 (semiconductor). FIXED: search_disruption_news query "global supply chain disruptions"; suppliers SUP-001, SUP-003; lanes Asia-Europe (Suez/Air), Intra-Europe (Road); regions Taiwan, Vietnam, Poland, Germany.
RULE: Threat level MUST come from perception_agent tool results only. Inventory/exposure from risk agent results.
"""
    if not enabled:
        # No tools → 1 API request per cycle (diagnostic)
        return """You are in diagnostic mode. You have NO tools. Do not call any function.
Reply with exactly the following text and nothing else:

═══ DIAGNOSTIC ═══
Sub-agents enabled: none (ORCHESTRATOR_SUBAGENTS is empty)
This cycle used 1 API request only. If you see 429, the limit is hit on that single request (TPM or RPM).
To add sub-agents: ORCHESTRATOR_SUBAGENTS=perception then perception,memory etc.
══════════════════
"""
    if enabled == list(SUBAGENT_ORDER):
        return _full_pipeline_instruction(profile)
    steps = [
        """
STEP 0 — RATE LIMIT (required first)
Call rate_limit_breather(message="ready"). Do not call any other tool until you receive its response.
"""
    ]
    if "perception" in enabled:
        steps.append("""
STEP 1 — PERCEIVE
Call the perception_agent with a message such as:
"Run a full disruption scan: (1) search_disruption_news for 'global supply chain disruptions', (2) get_shipping_lane_status for Asia-Europe (Suez), Asia-Europe (Air), Intra-Europe (Road), (3) get_climate_alerts for Taiwan, Vietnam, Poland, Germany, (4) score_supplier_health for SUP-001 and SUP-003. Return a structured summary with threat level (LOW/MEDIUM/HIGH/CRITICAL) and which signals need escalation."
Then call rate_limit_breather(message="next") before the next agent (if any).
""")
    if "memory" in enabled:
        steps.append("""
STEP 2 — MEMORY
Call the memory_learning_agent with a message such as:
"Retrieve similar past disruptions and recurring risk patterns. Use the disruption type and region from the perception summary. Return a Memory Brief: most relevant historical case, what worked/didn't, recurring patterns, and historical mitigation cost range."
Then call rate_limit_breather(message="next") before the next agent (if any).
""")
    if "risk" in enabled:
        steps.append("""
STEP 3 — RISK
Call the risk_intelligence_agent with a message such as:
"Assess risk for the current disruption. For affected suppliers (e.g. SUP-001, SUP-003): get disruption probability (30d), get_supplier_exposure, get_inventory_runway for SEMI-MCU-32, calculate_revenue_at_risk, calculate_sla_breach_probability for BMW Group and Volkswagen AG. Return a structured risk assessment."
Then call rate_limit_breather(message="next") before the next agent (if any).
""")
    if "planning" in enabled:
        steps.append("""
STEP 4 — PLAN
Call the scenario_planning_agent with a message such as:
"Given the risk assessment, simulate mitigation scenarios for SEMI-MCU-32: airfreight, buffer_build, alternate_supplier. Rank scenarios and create_planning_document with the top recommendation."
Then call rate_limit_breather(message="next") before the next agent (if any).
""")
    if "action" in enabled:
        steps.append("""
STEP 5 — ACTION
Call the action_execution_agent with a message such as:
"Execute actions: get_po_adjustment_suggestions, send_slack_alert to #supply-chain-alerts, draft_supplier_email if needed, flag_erp_reorder_adjustment. Return a list of actions taken."
Then call rate_limit_breather(message="next") if you will call memory_learning_agent again for logging.
""")
    steps.append("""
END EVERY RUN WITH:
═══ SUPPLY CHAIN OPERATIONS BRIEFING ═══
Timestamp: [time] | Threat Level: [from perception] | Signals: [N found]
Financial Exposure: $[X] | Inventory Runway: [X] days
Top Recommendation: [name] | Cost: $[X] | Actions: [summary]
═══════════════════════════════════════
""")
    return (
        "You are an Autonomous Supply Chain Resilience Agent for AutomotiveParts GmbH.\n"
        "You have the following specialist agents as tools. Run them in order. "
        "Before ANY sub-agent, call rate_limit_breather(message=\"ready\"). "
        "After EACH sub-agent, call rate_limit_breather(message=\"next\") before the next.\n"
        + profile
        + "\nPIPELINE — call each agent in order:\n"
        + "\n".join(steps)
    )


_enabled = _enabled_subagents()
# When no sub-agents: no tools → 1 API request per cycle (no tool round-trip that would cause 2nd request)
_tools = [rate_limit_breather] + [
    DelayedAgentTool(agent=SUBAGENT_AGENTS[name]) for name in _enabled
] if _enabled else []
root_agent = Agent(
    model=os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite-preview"),
    name="supply_chain_orchestrator",
    description=(
        "Autonomous Supply Chain Resilience Agent for AutomotiveParts GmbH. "
        "Delegates to perception, memory, risk, planning, and action sub-agents "
        "to monitor disruptions, assess risk, plan mitigation, and execute actions."
    ),
    instruction=_build_instruction(_enabled),
    tools=_tools,
)
