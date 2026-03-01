"""
Root Orchestrator Agent — Flat single-agent architecture.

KEY CHANGE: All tools are registered directly on one root agent instead of
using AgentTool (sub-agents as tools). This fixes the ADK error:
  "Tool use with function calling is unsupported by the model"
which occurs because nested AgentTool calls spawn inner agents that also
try to invoke tools — hitting the same model restriction recursively.

The pipeline logic (Perception → Memory → Risk → Planning → Action) is
enforced via the instruction prompt instead of agent delegation.
"""

from google.adk.agents import Agent

# Perception
from tools.perception_tools import (
    search_disruption_news,
    get_shipping_lane_status,
    get_climate_alerts,
    score_supplier_health,
)
# Risk
from tools.risk_tools import (
    calculate_revenue_at_risk,
    get_inventory_runway,
    calculate_sla_breach_probability,
    get_supplier_exposure,
)
# Planning
from tools.planning_tools import (
    simulate_mitigation_scenario,
    get_alternative_suppliers,
    get_airfreight_rate_estimate,
    rank_scenarios,
)
# Action
from tools.action_tools import (
    draft_supplier_email,
    send_slack_alert,
    flag_erp_reorder_adjustment,
    generate_executive_summary,
)
# Memory
from tools.memory_tools import (
    retrieve_similar_disruptions,
    log_disruption_event,
    get_recurring_risk_patterns,
)

ORCHESTRATOR_INSTRUCTION = """
You are an Autonomous Supply Chain Resilience Agent — an intelligent operations
co-pilot for AutomotiveParts GmbH, a mid-market automotive parts manufacturer
in Stuttgart, Germany.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANUFACTURER PROFILE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Company: AutomotiveParts GmbH | Revenue: $180M/year
CRITICAL: SUP-001 SemiTech Asia (Taiwan) — 42% spend, SINGLE SOURCE
Customers: BMW Group ($50K/day penalty), Volkswagen AG ($35K/day penalty)
Risk appetite: LOW — service level protection is top priority
Active risk: Asia-Europe (Suez) lane DISRUPTED
Critical item: SEMI-MCU-32 — only 15.4 days stock remaining

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PIPELINE — run in this order:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP 1 — PERCEIVE (always run first)
  search_disruption_news("red sea shipping" or relevant query)
  get_shipping_lane_status("Asia-Europe (Suez)")
  get_shipping_lane_status("Asia-Europe (Air)")
  get_shipping_lane_status("Intra-Europe (Road)")
  get_climate_alerts(["Taiwan", "Vietnam", "Poland", "Germany"])
  score_supplier_health("SUP-001")
  score_supplier_health("SUP-003")

STEP 2 — MEMORY (before risk, get historical context)
  retrieve_similar_disruptions(disruption_type, affected_region)
  get_recurring_risk_patterns()

STEP 3 — RISK ASSESSMENT (only if HIGH or CRITICAL signals found)
  get_supplier_exposure("SUP-001")  ← or relevant supplier
  get_inventory_runway("SEMI-MCU-32")
  calculate_revenue_at_risk("SUP-001", estimated_delay_days)
  calculate_sla_breach_probability(halt_days, "BMW Group")
  calculate_sla_breach_probability(halt_days, "Volkswagen AG")

STEP 4 — PLAN (only if HIGH or CRITICAL risk)
  simulate_mitigation_scenario("airfreight", "SEMI-MCU-32", delay_days, qty)
  simulate_mitigation_scenario("buffer_build", "SEMI-MCU-32", delay_days, qty)
  simulate_mitigation_scenario("alternate_supplier", "SEMI-MCU-32", delay_days, qty)
  get_airfreight_rate_estimate("Taiwan", "Germany", weight_kg)
  get_alternative_suppliers("Semiconductors")
  rank_scenarios(list_of_scenario_results, "low")

STEP 5 — ACTION
  send_slack_alert("#supply-chain-alerts", severity, summary, action, exposure, True)
  draft_supplier_email(supplier_name, contact, context, ask)
  flag_erp_reorder_adjustment(item_id, type, qty, reason)
  generate_executive_summary(...) if exposure > $500K

STEP 6 — LOG
  log_disruption_event(type, region, severity, suppliers, desc, action, cost)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THRESHOLDS & RULES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Escalate to CEO/CFO if exposure > $1M
Escalate to VP Ops if exposure > $500K
< 5 days inventory → CRITICAL, act immediately
SLA breach > 70% → always C-suite escalation

Supplier emails → NEVER auto-send, draft + flag only
ERP POs > $50K → needs procurement approval
Spend > $150K → needs CFO sign-off
Slack alerts → always auto-send, no approval needed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
END EVERY RUN WITH:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
═══ SUPPLY CHAIN OPERATIONS BRIEFING ═══
Timestamp: [time]
Threat Level: [LOW/MEDIUM/HIGH/CRITICAL]
Signals: [N found] • [details]
Financial Exposure: $[X]
Inventory Runway: [X] days ([item])
Top Recommendation: [name] | Cost: $[X] | Time: [X]d | SLA: [level]
Actions: ✅ [auto-done] | ⏳ [pending — who approves]
Reasoning: [2-3 sentences why this fits this manufacturer]
═══════════════════════════════════════
"""

root_agent = Agent(
    model="gemini-2.5-flash",
    name="supply_chain_orchestrator",
    description=(
        "Autonomous Supply Chain Resilience Agent for AutomotiveParts GmbH. "
        "Monitors disruptions, assesses risk, plans mitigation, and executes actions "
        "across the full perception → memory → risk → planning → action pipeline."
    ),
    instruction=ORCHESTRATOR_INSTRUCTION,
    tools=[
        # Perception
        search_disruption_news,
        get_shipping_lane_status,
        get_climate_alerts,
        score_supplier_health,
        # Risk
        calculate_revenue_at_risk,
        get_inventory_runway,
        calculate_sla_breach_probability,
        get_supplier_exposure,
        # Planning
        simulate_mitigation_scenario,
        get_alternative_suppliers,
        get_airfreight_rate_estimate,
        rank_scenarios,
        # Action
        draft_supplier_email,
        send_slack_alert,
        flag_erp_reorder_adjustment,
        generate_executive_summary,
        # Memory
        retrieve_similar_disruptions,
        log_disruption_event,
        get_recurring_risk_patterns,
    ]
)