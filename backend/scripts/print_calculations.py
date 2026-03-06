#!/usr/bin/env python3
"""
Print a short "how metrics are calculated" summary for demos or presentations.
Run from project root: python scripts/print_calculations.py
"""

def main():
    print("""
═══════════════════════════════════════════════════════════════════
  SUPPLY CHAIN RESILIENCE AGENT — How metrics are calculated
═══════════════════════════════════════════════════════════════════

DASHBOARD KPIs (ui/app/api/dashboard/route.ts)
───────────────────────────────────────────────
• Disruption risk (0–100):
  criticalCount×15 + highCount×8 + (pendingCount/activeCount)×20
  + min(20, totalRevenueAtRisk/1M)  → capped at 100

• Revenue at risk ($):
  Sum of impact.revenue_at_risk_usd across active disruptions

• Pending approvals:
  Mock events with outcome "Pending" (not in approval_resolutions)
  + count of status="pending" in data/pending_approvals.json

• Logistics freight (0–100):
  (disruptions matching shipping/suez/canal/freight/port etc.) / activeCount × 100

• Supplier concentration (0–100, base 0):
  maxSpendPct + singleSourceCount×40 + (supplier_health_degraded ? 15 : 0)
  → max(0, …), min(100, …)

RISK TOOLS (tools/risk_tools.py)
────────────────────────────────
• Revenue at risk: daily_revenue × max(0, delay_days - days_on_hand) per line; + SLA penalties
• SLA breach probability: min(1, production_halt_days × 0.08)
• Supplier exposure: flags (spend>35%, single source, health<70, lead>30d); CRITICAL if ≥3 flags

PLANNING (tools/planning_tools.py + planning_config.json)
────────────────────────────────────────────────────────
• Scenario cost: (base_unit_cost × (1 + premium_pct/100)) × qty + fixed_cost; incremental = total - baseline
• Scenario rank: adjusted_score = w.service×service + w.cost×cost + w.speed×speed
  (weights from risk_appetite_weights, e.g. low: 0.6/0.25/0.15); sort descending → top_recommendation

APPROVALS
─────────
• Inbox = pending_approvals.json (status pending) + mock events with outcome "Pending" not in approval_resolutions.json
• Agent adds items via submit_mitigation_for_approval() → ui/data/pending_approvals.json

Full script: scripts/PRESENTATION_SCRIPT.md
═══════════════════════════════════════════════════════════════════
""")

if __name__ == "__main__":
    main()
