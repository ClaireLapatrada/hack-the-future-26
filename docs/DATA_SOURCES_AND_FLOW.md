# Where the briefing data comes from & how it works

When you ask **"any disruption?"**, the orchestrator runs a single **root agent** (Gemini 2.5 Flash) with **all tools** attached. The agent follows the pipeline in its **instruction** (Perception → Memory → Risk → Planning → Action → Log) and then formats the final **Supply Chain Operations Briefing**. Here is where each part of that briefing comes from.

---

## 1. How it works (high level)

- **One agent, many tools**  
  There is no sub-agent delegation. The orchestrator in `orchestrator_agent/agent.py` has one `Agent` with tools from `tools/perception_tools.py`, `risk_tools.py`, `planning_tools.py`, `action_tools.py`, and `memory_tools.py`. The **instruction** tells the model to call tools in order (Perception → Memory → Risk → Planning → Action) and then output the briefing block.

- **Data sources**  
  Numbers and statuses come from **mock JSON files** and **config** in the repo. Some perception (e.g. supplier health) can use the **Gemini API**; shipping/climate can use **real APIs** if you set the right env vars (see `docs/PERCEPTION_APIS.md`).

---

## 2. Where each briefing line comes from

| Briefing line | Source | How |
|---------------|--------|-----|
| **Threat Level: CRITICAL** | LLM | Model infers from tool results (e.g. disrupted lane + single-source supplier + low runway). |
| **Signals: 2 found • [CRITICAL] Asia–Europe (Suez) … 16 days … • [CRITICAL] SUP-001 … health declining …** | Perception tools + config | • **Suez, 16 days:** `get_shipping_lane_status("Asia-Europe (Suez)")` in `tools/perception_tools.py` returns a **hardcoded mock**: `status: "DISRUPTED"`, `avg_delay_days: 16`. • **SUP-001 (SemiTech Asia) health declining, geopolitical:** `score_supplier_health("SUP-001")` loads supplier from `config/manufacturer_profile.json` (or `mock_profile.json`) and calls the **Gemini API** to score health; the model returns fields like `trend: "Declining"`, `geopolitical_risk_exposure: "High"`. |
| **Financial Exposure: $1,832,000** | Risk tools + ERP + config | `calculate_revenue_at_risk("SUP-001", estimated_delay_days)` in `tools/risk_tools.py` uses **`data/mock_erp.json`** (inventory, e.g. SEMI-MCU-32) and **`config/manufacturer_profile.json`** (production_lines, customer_slas) to compute revenue at risk + SLA penalties. The LLM passes a delay (e.g. 16) from the Suez status; the tool returns `total_financial_exposure_usd`. |
| **Inventory Runway: 12.0 days (SEMI-MCU-32)** | Risk tools + ERP | `get_inventory_runway("SEMI-MCU-32")` in `tools/risk_tools.py` reads **`data/mock_erp.json`**. That file has `"days_on_hand": 12` for SEMI-MCU-32, so the briefing shows **12.0 days**. |
| **Top Recommendation: Emergency Airfreight \| Cost: $79,000 \| Time: 2d \| SLA: High** | Planning tools + config | The LLM calls `simulate_mitigation_scenario("airfreight", "SEMI-MCU-32", delay_days, quantity_needed)` and/or `get_airfreight_rate_estimate("Taiwan", "Germany", weight_kg)`. **`planning_config.json`** defines the airfreight scenario (e.g. `fixed_cost_usd: 15000`, `implementation_days: 2`, `service_level_protection: "High"`, unit cost premium). The **$79,000** is the scenario total for the quantity/weight the model chose (or from a previous run that was logged). |
| **Actions: ✅ Slack … \| ✅ ERP … \| ✅ Supplier email … \| ✅ Executive summary \| ⏳ Pending …** | Action tools + instruction | The LLM calls `send_slack_alert`, `flag_erp_reorder_adjustment`, `draft_supplier_email`, `generate_executive_summary`. The instruction says: Slack always auto-send; ERP POs > $50K need procurement approval; spend > $150K needs CFO sign-off. So **$79K airfreight** is summarized as **pending CFO & Procurement approval**. |
| **Reasoning: …** | LLM | The model writes 2–3 sentences from the instruction ("why this fits this manufacturer") using the tool outputs. |
| **Timestamp** | Generated at response time | Filled by the model (e.g. `2026-02-28T11:25:27.234Z`). |

After the run, the agent can call **`log_disruption_event(...)`** in `tools/memory_tools.py`, which appends to **`mock_disruption_history.json`** (or uses Qdrant if configured). So a **logged event** (e.g. EVT-2026-0228-004 with `cost_usd: 79000`) can match the same run's recommendation.

---

## 3. File reference

| File | Used by | Purpose |
|-----|--------|--------|
| **`config/manufacturer_profile.json`** | Risk tools, Perception (supplier health) | Suppliers (SUP-001…), production_lines, customer_slas, inventory_policy. |
| **`data/mock_erp.json`** | Risk tools | Inventory (e.g. SEMI-MCU-32, days_on_hand: 12), open_purchase_orders. |
| **`mock_profile.json`** | Perception (fallback), reference | Same structure as manufacturer_profile; used if config not present. |
| **`planning_config.json`** | Planning tools | Scenario definitions (airfreight, buffer_build, …), airfreight_rates, defaults. |
| **`mock_disruption_history.json`** | Memory tools | Past events; `retrieve_similar_disruptions`, `get_recurring_risk_patterns`; new events from `log_disruption_event`. |
| **`tools/perception_tools.py`** | Orchestrator | `get_shipping_lane_status` (mock Suez 16-day delay), `score_supplier_health` (Gemini), search/climate if configured. |

---

## 4. Summary

- **Single agent** with one instruction and many tools runs the full pipeline and then formats the briefing.
- **Disruption and delay** (Suez, 16 days) come from **mock data** in `get_shipping_lane_status`.
- **Supplier health** (SUP-001 declining, geopolitical) comes from **Gemini** in `score_supplier_health` plus **config/manufacturer_profile.json** (or mock_profile).
- **Financial exposure** and **inventory runway** come from **risk_tools** using **data/mock_erp.json** and **config/manufacturer_profile.json**.
- **Recommendation** (airfreight, cost, time, SLA) comes from **planning_tools** and **planning_config.json**.
- **Actions** come from **action_tools**; "pending approval" comes from the **orchestrator instruction** rules.

To use **real** disruption or shipping data, you'd plug in live APIs (see `docs/PERCEPTION_APIS.md`) and keep the same tool interfaces; the briefing format would stay the same.
