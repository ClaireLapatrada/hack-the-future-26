# Agents, Tools, and Calculations — Detailed Reference

This document describes each agent (as defined in the codebase), every tool they use, and the **calculations and logic** in detail. Code paths are referenced so the doc stays accurate.

---

## 1. Root agent: Supply Chain Orchestrator

- **Files:** `orchestrator_agent/agent.py` (sub-agent mode, default), `orchestrator_agent/agent_flat.py` (flat mode).
- **Model:** `GEMINI_MODEL` (default `gemini-3.1-flash-lite-preview`)
- **Role:** Runs the full pipeline (Perception → Memory → Risk → Planning → Action). **Two variants:**
  - **Sub-agent mode:** Root agent has **sub-agents as tools** via `DelayedAgentTool` (perception_agent, memory_agent, risk_agent, planning_agent, action_agent) plus `rate_limit_breather`. By default all five sub-agents are enabled; instruction uses `_full_pipeline_instruction(profile)`. Sub-agents are invoked in order; each sub-agent’s tools are wrapped with `with_reasoning_log` so the UI stream matches flat mode.
  - **Flat mode** (`ORCHESTRATOR_USE_FLAT=1`): Single root agent with **all tools** registered directly; pipeline enforced in the instruction. All tools wrapped with `with_reasoning_log`.
- **Tools (flat):** All perception, memory, risk, planning, and action tools listed below. **Tools (sub-agent):** `rate_limit_breather` + one tool per enabled sub-agent (each sub-agent exposes its own tools internally with `with_reasoning_log`).

---

## 2. Perception (signals)

**Agent module:** `perception_agent/agent.py` — invoked as a sub-agent in sub-agent mode; its tools are wrapped with `with_reasoning_log`. In flat mode the same tools run on the root agent.

### 2.1 `search_disruption_news(query: str)`

- **Purpose:** Search for supply chain disruption news via Google Custom Search.
- **Inputs:** `query` — e.g. `"global supply chain disruptions"` (fixed in orchestrator instruction).
- **Data source:** Google Custom Search JSON API (`GOOGLE_SEARCH_API_KEY` or `GOOGLE_API_KEY`, `GOOGLE_SEARCH_ENGINE_ID`).
- **Logic:**
  - Call `https://www.googleapis.com/customsearch/v1` with `key`, `cx`, `q`, `num`.
  - Parse `items[]`; for each: `title`, `displayLink`, `link`, `snippet`, optional `pagemap.metatags` for publish date.
  - Return list of signals with `title`, `source`, `published`, `url`, `summary`; `classified_type`, `severity`, `confidence_score` left null.
- **Output:** `status`, `query`, `articles_found`, `signals[]`, `scan_timestamp`. On 403/error: `status: "error"`, `message` with setup hints.

### 2.2 `get_shipping_lane_status(lane: str)`

- **Purpose:** Get operational status of a shipping lane (OPERATIONAL or DISRUPTED).
- **Inputs:** `lane` — e.g. `"Asia-Europe (Suez)"`, `"Asia-Europe (Air)"`, `"Intra-Europe (Road)"`.
- **Data source:** `config/active_disruption.json`; if not active or lane not disrupted, falls back to `search_disruption_news(f'"{lane}" shipping disruption')`.
- **Logic:**
  - If `active_disruption.json` has `active: true` and `shipping_lanes[lane].status == "DISRUPTED"`: return that lane’s config (severity, avg_delay_days, reroute_available, etc.).
  - Else: run news search for the lane; if `articles_found == 0` or no signals → return default OPERATIONAL status.
  - If articles found: infer DISRUPTED from keywords (e.g. "blockade", "closed", "suez", "red sea"); severity "High" for canal/blockade; try to parse delay days from text with regex `(\d+)\s*day`, else 7–10 days; set `reroute_via` "Cape of Good Hope" if "cape" in text.
- **Output:** `status`, `lane`, `lane_status` (status, severity, avg_delay_days, reroute_available, reroute_via, etc.).

### 2.3 `get_climate_alerts(regions: list[str])`

- **Purpose:** Fetch active climate/natural disaster alerts for given regions (NASA EONET).
- **Inputs:** `regions` — e.g. `["Taiwan", "Vietnam", "Poland", "Germany"]`.
- **Data source:** NASA EONET API v3 (`https://eonet.gsfc.nasa.gov/api/v3/events`), optional `NASA_API_KEY`.
- **Logic:**
  - Request `status=open`, `days=30`, `limit=100`.
  - For each region, use bounding box `_REGION_BBOX` (e.g. Taiwan, Vietnam, Germany, Poland); filter events whose geometry (Point or Polygon) intersects the box.
  - Per event: category title, title, magnitude (if present); severity "High" if magnitude ≥ 60, else "Medium" if ≥ 35, else "Low".
  - Build list of alerts per region: type, name, severity, affected_area, logistics_disruption_risk.
- **Output:** `status`, `regions_checked`, `alerts`: `{ region: { active_alerts: [...] } }`, `scan_timestamp`.

### 2.4 `score_supplier_health(supplier_id: str)`

- **Purpose:** Score a supplier’s financial/operational health.
- **Inputs:** `supplier_id` — e.g. `"SUP-001"`, `"SUP-003"`.
- **Data source:** `config/manufacturer_profile.json` or `mock_profile.json` for supplier metadata; `config/active_disruption.json` for `supplier_health_degraded`.
- **Logic:**
  - If `active_disruption.supplier_health_degraded` is not true: return static healthy response (overall_health_score 85, financial_stability "Strong", etc.).
  - Else: load supplier from profile; call Gemini with a structured prompt to return JSON: `overall_health_score` (0–100), `financial_stability`, `payment_behavior`, `operational_reliability`, `geopolitical_risk_exposure`, `recent_flags`, `trend`, `recommendation`.
- **Output:** `status`, `supplier_id`, `health_data` (or error message if Gemini unavailable).

---

## 3. Memory (historical context)

**Agent module:** `memory_agent/agent.py` — invoked as a sub-agent in sub-agent mode; its tools use `with_reasoning_log`. In flat mode the same tools run on the root agent.

### 3.1 `retrieve_similar_disruptions(disruption_type, affected_region, top_k=3)`

- **Purpose:** Retrieve historically similar disruptions and mitigation outcomes.
- **Inputs:** `disruption_type` (e.g. "Shipping Disruption"), `affected_region` (e.g. "Red Sea", "Taiwan"), `top_k`.
- **Data source:** `data/mock_disruption_history.json` (or project root / `ui/data/`); optionally Qdrant when `QDRANT_URL` and `GEMINI_API_KEY` are set.
- **Logic:**
  - **With Qdrant:** Embed query text `f"{disruption_type} {affected_region}"` via Gemini `embed_content` (model `gemini-embedding-001`); if collection empty, backfill from JSON history; then `client.search` with query vector, limit `top_k`. Return payloads with event_id, date, type, description, mitigation action/outcome/cost, lesson.
  - **Without Qdrant:** Load JSON history; relevance score = +3 for type match, +3 for region in event region, +2 for region in description, +1 for type in description; sort by score, take top_k with score > 0.
- **Output:** `status`, `query`, `similar_cases_found`, `cases[]` (event_id, date, type, description, what_worked, outcome, cost_usd, actual_loss_usd, lesson), `summary`.

### 3.2 `get_recurring_risk_patterns()`

- **Purpose:** Analyze disruption history to identify recurring risk patterns.
- **Data source:** Same disruption history JSON.
- **Logic:**
  - Count by type, by supplier, by region; sum `actual_revenue_lost_usd` and `mitigation_taken.cost_usd`.
  - Most affected supplier / most common type / most affected region (max count).
  - Patterns: if a supplier appears ≥ 2 times → "Recurring Supplier Risk"; if a type ≥ 2 → "Recurring Disruption Type"; if a region ≥ 2 → "High-Risk Region". Each with detail and recommendation.
- **Output:** `status`, `total_events_analyzed`, `total_historical_losses_usd`, `total_mitigation_costs_usd`, `disruption_by_type`, `disruption_by_region`, `most_affected_suppliers`, `recurring_patterns[]`, `summary`.

### 3.3 `log_disruption_event(event_type, region, severity, affected_suppliers, description, mitigation_action, estimated_cost_usd, outcome="Pending")`

- **Purpose:** Log a new disruption event for future learning.
- **Logic:** Build event dict with `event_id` (EVT-YYYY-MMDD-NNN), date, type, region, severity, affected_suppliers, description, impact (placeholder), mitigation_taken (action, cost_usd, outcome), lessons_learned; append to history JSON; if Qdrant available, embed `_event_to_text(event)` and upsert to collection.
- **Output:** `status`, `event_id`, `logged_event`, `storage_status`, note about Qdrant.

---

## 4. Risk (exposure and probability)

**Agent module:** `risk_agent/agent.py` — invoked as a sub-agent in sub-agent mode; its tools use `with_reasoning_log`. In flat mode the same tools run on the root agent.

**Data sources:** `data/mock_erp.json` (or `ERP_JSON_PATH`), `config/manufacturer_profile.json` (or `MANUFACTURER_PROFILE_PATH`), `data/mock_disruption_history.json` (or project root), `config/active_disruption.json`. Optional trained model: `data/risk_model.joblib` + `data/risk_model_features.json`.

### 4.1 `calculate_revenue_at_risk(affected_supplier_id, estimated_delay_days)`

- **Purpose:** Revenue and SLA exposure if a supplier is disrupted for N days.
- **Logic:**
  - From ERP, select inventory items where `supplier_id == affected_supplier_id`.
  - For each item: `days_on_hand`; `buffer_after_stock_out = max(0, estimated_delay_days - days_on_hand)`.
  - Map items to production lines: SEMI* → semiconductor_dependent lines, STEEL* → non-semiconductor. For each matching line: `revenue_at_risk = daily_revenue_usd * buffer_after_stock_out`; accumulate `total_revenue_at_risk`, build `at_risk_lines` with line_id, product, days_on_hand, stockout_day, production_halt_days, daily_revenue_usd, revenue_at_risk_usd.
  - SLA: for each customer SLA, `halt_days = max(production_halt_days across at_risk_lines)`; `sla_penalties += penalty_per_day_usd * halt_days`.
- **Output:** `total_revenue_at_risk_usd`, `sla_penalties_at_risk_usd`, `total_financial_exposure_usd`, `affected_production_lines`, `summary`.

### 4.2 `get_inventory_runway(item_id)`

- **Purpose:** Days of inventory left for an item and alert level.
- **Logic:** Find item in ERP; from profile `inventory_policy` get `reorder_threshold_days`, `target_buffer_days`. `alert_level`: CRITICAL if `days_on_hand <= reorder_threshold`, WARNING if `<= target_buffer*0.5`, LOW if `< target_buffer`, else OK.
- **Output:** `item_id`, `description`, `supplier_id`, `days_on_hand`, `daily_consumption`, `stock_units`, `on_order_units`, `expected_delivery_date`, `reorder_threshold_days`, `target_buffer_days`, `alert_level`, `days_until_stockout`, `summary`.

### 4.3 `calculate_sla_breach_probability(production_halt_days, customer_name)`

- **Purpose:** Probability of breaching a customer SLA given expected halt.
- **Logic:** Find customer SLA in profile. **Formula:** `breach_probability = min(1.0, production_halt_days * 0.08)`. `penalty_exposure = penalty_per_day_usd * production_halt_days`. Severity: CRITICAL if breach > 0.7, HIGH if > 0.4, else MEDIUM.
- **Output:** `customer`, `sla_target_pct`, `production_halt_days`, `breach_probability`, `breach_probability_pct`, `penalty_per_day_usd`, `total_penalty_exposure_usd`, `severity`.

### 4.4 `get_supplier_exposure(supplier_id)`

- **Purpose:** Full operational exposure profile for a supplier.
- **Logic:** Load supplier from profile; open POs from ERP for that supplier, sum `value_usd`. Risk flags: spend_pct > 35 → concentration; single_source → single source; health_score < 70 → low health; lead_time_days > 30 → long lead time. `overall_risk`: CRITICAL if ≥ 3 flags, HIGH if ≥ 2, else MEDIUM.
- **Output:** `supplier`, `open_purchase_orders`, `total_open_po_value_usd`, `risk_flags[]`, `overall_risk_rating`, `summary`.

### 4.5 `get_disruption_probability(supplier_id, time_horizon_days=30, news_signals_json=None, climate_alerts_json=None, shipping_lane_status_json=None, supplier_health_json=None)`

- **Purpose:** P(disruption) for supplier over time horizon; risk classification and primary drivers.
- **Logic:**
  - **Indicators (0–1):**
    - **Delivery delay frequency:** From disruption history, count events affecting this supplier with delay_days > 0; `delivery_delay_frequency = min(1, (delay_events / total_events) * 2)`.
    - **Financial health risk:** `1 - (health_score/100)`; health_score can be overridden from `supplier_health_json`.
    - **Region instability:** From climate_alerts for supplier country + news_signals; base `min(1, alerts*0.2 + news*0.05)`; +0.2 if Taiwan or Vietnam.
    - **Logistics congestion:** 0.7 if lane DISRUPTED and severity High, else 0.4 if disrupted, else 0.
    - **Weather disruption prob:** `min(1, len(region_alerts)*0.15)`.
  - **Model:** If `risk_model.joblib` exists: feature vector = [financial_health_risk, delivery_delay_frequency, region_instability, logistics_congestion, weather_disruption_prob, single_source 0/1, spend_pct/100]; `predict_proba`; then `p_disruption = p_low*0.15 + p_med*0.50 + p_high*0.85`; classification from model.
  - **Else (weighted formula):** `w_health=0.25, w_region=0.25, w_logistics=0.25, w_delivery=0.15, w_weather=0.10`; `p_disruption = weighted sum`; if single_source multiply by 1.15; if spend_pct>35 multiply by 1.1; cap at 1. Classification: <35% Low, <65% Medium, else High.
  - **Primary drivers:** List contributing factors (e.g. financial health, region instability, logistics, delivery history, weather, single-source, spend concentration).
- **Output:** `supplier_id`, `supplier_name`, `time_horizon_days`, `disruption_probability_pct`, `risk_classification`, `primary_drivers[]`, `risk_indicators` (all component scores), `summary`.

### 4.6 `estimate_revenue_at_risk_executive(operational_impact_json=None)`

- **Purpose:** Executive summary of revenue-at-risk, margin impact, SLA penalties, best/expected/worst case.
- **Logic:** If no JSON, call `get_operational_impact()`. When the model passes **parsed impact JSON** (e.g. from a prior tool result), the tool accepts it without requiring `"status": "success"`; it only treats as error when the parsed JSON has `"status": "error"`. From impact: affected_production_lines (at_risk), estimated_delay_days_min/max; delay_mid = (min+max)//2. Margin rate 30%. For each of min/mid/max delay: `revenue_at_risk = sum(daily_revenue_usd of at_risk lines) * delay_days`; `sla_penalties = sum(penalty_per_day_usd) * delay_days`; `margin_impact = revenue_at_risk * 0.30`. Expected = mid case; customers_affected = len(customer_slas).
- **Output:** `revenue_at_risk_usd`, `margin_impact_usd`, `sla_penalties_usd`, `customers_affected`, `best_case`, `expected_case`, `worst_case` (each with delay_days, revenue_at_risk_usd, sla_penalties_usd, margin_impact_usd), `summary`.

### 4.7 `get_operational_impact(affected_supplier_id=None, disruption_days_assumed=None, simulation_runs=500)` (operational_impact_tools)

- **Purpose:** Production downtime probability, affected lines, delay range, critical dependencies.
- **Logic:** Load profile, ERP, active_disruption. Resolve delay_min/delay_max from active lanes or default 5–15. Build line→items (SEMI→semiconductor lines, STEEL→non-semiconductor). Critical dependencies = items per line with supplier_id, single_source, line_id. At-risk lines: if affected_supplier_id set, lines using that supplier; else all lines with single-source components. Monte Carlo: `simulation_runs` times sample disruption_days; for each at-risk line check if any component from disrupted supplier has days_on_hand < disruption_days → shutdown; count shutdowns. `production_downtime_probability_pct = 100 * shutdown_count / simulation_runs`.
- **Output:** `production_downtime_probability_pct`, `affected_production_lines` (line_id, product, daily_revenue_usd, at_risk), `estimated_delay_days_min/max`, `critical_component_dependencies`, `summary`.

---

## 5. Planning (scenarios and documents)

**Agent module:** `planning_agent/agent.py` — invoked as a sub-agent in sub-agent mode; its tools use `with_reasoning_log`. In flat mode the same tools run on the root agent.

**Config:** `planning_config.json` (or `PLANNING_CONFIG_PATH`): scenario_definitions, alternative_suppliers, airfreight_rates, airfreight_defaults, risk_appetite_weights, service_level_scores, rank_service_scores, buffer_stock_defaults.

### 5.1 `simulate_mitigation_scenario(scenario_type, affected_item_id, disruption_days, quantity_needed)`

- **Purpose:** Single scenario cost, time, service level.
- **Logic:** Look up scenario in config (e.g. airfreight, buffer_build, alternate_supplier). `premium_unit_cost = base_unit_cost_usd * (1 + unit_cost_premium_pct/100)`; `variable_cost = premium_unit_cost * quantity_needed`; `total_cost = variable_cost + fixed_cost_usd`; `incremental_cost = total_cost - baseline_cost` (baseline = base_unit_cost * quantity). Service score from SERVICE_LEVEL_SCORES; cost_score = max(0, 100 - unit_cost_premium_pct/3); speed_score = max(0, 100 - implementation_days*4). **Composite score:** `service*0.5 + cost*0.3 + speed*0.2`.
- **Output:** `scenario_type`, `scenario_name`, `description`, `financials` (incremental_cost_usd, total_cost_usd, unit_cost_premium_pct), `timing` (implementation_days, lead_time_reduction_days), `service_level_protection`, `risks`, `composite_score`, `co2_impact`.

### 5.2 `rank_scenarios(scenarios_json, risk_appetite="low")`

- **Purpose:** Rank scenarios by risk-appetite-adjusted score.
- **Logic:** Parse JSON array of scenario objects (each with service_level_protection, financials.unit_cost_premium_pct, timing.implementation_days). **Tolerant of model output:** `financials` and `timing` may be strings (e.g. `"1-3 days"`) or non-dict; the code treats non-dict as `{}` and skips invalid entries. Weights from config: low = service 0.6, cost 0.25, speed 0.15; medium/high differ. `service_score = RANK_SERVICE_SCORES[service_level]` (High 100, Medium 60, Low 20); `cost_score = max(0, 100 - unit_cost_premium_pct/3)`; `speed_score = max(0, 100 - implementation_days*3)`. `adjusted_score = service*w.service + cost*w.cost + speed*w.speed`. Sort by adjusted_score descending.
- **Output:** `risk_appetite`, `ranked_scenarios[]`, `top_recommendation` (name), `reasoning`.

### 5.3 `run_scenario_simulation(disruption_days_min, disruption_days_max, quantity_needed, affected_item_id, risk_appetite, monte_carlo_runs=200)`

- **Purpose:** Monte Carlo comparison of all scenarios; recommended scenario and expected cost/service.
- **Logic:** For each run: sample disruption_days and demand multiplier (0.9–1.1); for each scenario type compute incremental_cost, total_cost, service/speed/cost scores, adjusted score (same weights as rank_scenarios). Aggregate per scenario: avg incremental_cost, avg adjusted_score. Build comparison_table; sort by average_score; recommended = top. `expected_cost_increase_pct = 100 * expected_cost_increase_usd / baseline_cost`.
- **Output:** `scenario_comparison_table`, `recommended_scenario`, `recommended_scenario_id`, `expected_service_level_performance`, `expected_cost_increase_usd`, `expected_cost_increase_pct`, `disruption_resilience_improvement`, `monte_carlo_runs`, `risk_appetite`, `summary`.

### 5.4 `evaluate_mitigation_tradeoffs(disruption_days, quantity_needed, affected_item_id, risk_appetite)`

- **Purpose:** Wrapper for run_scenario_simulation with delay range ±5 days, 100 runs; returns recommended strategy, cost vs resilience, service-level impact.
- **Output:** `recommended_strategy`, `scenarios[]`, `cost_vs_resilience`, `service_level_impact`, `summary`.

### 5.5 `create_planning_document(title, situation_summary, recommended_scenario, scenario_comparison_json, cost_impact_summary, service_level_impact, document_type, affected_item_id, risk_appetite)`

- **Purpose:** Persist a planning document for Past crisis / Mitigation UI.
- **Logic:** Generate `doc_id` (PLAN-YYYYMMDD-HHMMSS), slug from title; parse scenario_comparison_json; build doc object; append to `ui/data/planning_documents.json`.
- **Output:** `status`, `document_id`, `slug`, `path` (/planning-documents/{id}), message.

### 5.6 `get_alternative_suppliers(category, exclude_regions=None)`

- **Purpose:** List alternative suppliers for a category from config.
- **Logic:** Read ALTERNATIVE_SUPPLIERS[category]; filter out exclude_regions.
- **Output:** `category`, `excluded_regions`, `alternatives_found`, `alternative_suppliers[]`.

### 5.7 `get_airfreight_rate_estimate(origin_country, destination_country, weight_kg)`

- **Purpose:** Airfreight cost estimate for emergency shipments.
- **Logic:** Route key `origin|destination`; rate from AIRFREIGHT_RATES or defaults (rate_per_kg, transit_days); `total_cost = rate_per_kg * weight_kg`; add handling_fee_usd and customs (total_cost * customs_pct).
- **Output:** `origin`, `destination`, `weight_kg`, `rate_per_kg_usd`, `transit_days`, `freight_cost_usd`, `handling_fee_usd`, `customs_estimate_usd`, `total_estimated_cost_usd`.

### 5.8 `optimize_supplier_reallocation(demand_units=None, disruption_probabilities_json=None)`

- **Purpose:** Optimal allocation across suppliers; cost and risk penalty.
- **Logic:** Load profile suppliers; parse disruption probs per supplier. Total demand from param or ERP (sum of daily_consumption*30). Per supplier: capacity_share from spend_pct; unit_cost 12.5; reliability from health; risk_penalty_scale 500. Allocation: share = capacity_share / total_capacity; alloc = demand * share; cost = alloc * unit_cost; risk_penalty = alloc * disruption_prob * scale / 1000. Concentration before/after from max spend_pct / max allocation_pct; disruption_exposure_pct = weighted avg of allocation_pct * prob.
- **Output:** `allocation_by_supplier`, `total_demand_units`, `total_cost_usd`, `total_risk_penalty_usd`, `cost_impact`, `concentration_risk_reduction_pct`, `disruption_exposure_pct`, `summary`.

### 5.9 `recommend_buffer_stock(item_id, service_level_target_pct, holding_cost_pct_per_year, stockout_cost_per_unit)`

- **Purpose:** Recommended safety stock (days), stockout probability before/after, inventory cost impact.
- **Logic:** Load item from ERP; profile inventory_policy (target_buffer_days, max_buffer_days). Demand CV and lead time std from config. `sigma_LT = sqrt(demand_std_daily^2 * lead_time_days + (daily_consumption * lead_time_std)^2)`. Z from service level (e.g. 95% → 1.65). `safety_stock_units = Z * sigma_LT`; `safety_stock_days = safety_stock_units / daily_consumption`. Min days for target service (e.g. 95% → 14 days). **Stockout probability:** `_stockout_probability_from_days(days_on_hand)`: ~18% at 12 days, ~4% at 14 days, 25% at ≤10, 1% at ≥20; linear interpolation between. Inventory cost before/after = (days/365) * daily_consumption * 12.5 * (holding_pct/100); cost_increase_pct.
- **Output:** `item_id`, `recommended_safety_stock_days`, `recommended_safety_stock_units`, `stockout_probability_before_pct`, `stockout_probability_after_pct`, `inventory_carrying_cost_before_usd`, `inventory_carrying_cost_after_usd`, `inventory_cost_increase_pct`, `impact_summary`, `summary`.

---

## 6. Action (execution and approvals)

**Agent module:** `action_agent/agent.py` — invoked as a sub-agent in sub-agent mode; its tools use `with_reasoning_log`. In flat mode the same tools run on the root agent.

**Config:** `config/action_config.json`: po_adjustment (auto_restock_threshold_usd, reorder_threshold_days, target_buffer_days, max_auto_restock_quantity_per_line), escalation_triggers, decision_transparency.include_in_escalation, client_context, workflow_integrations.

### 6.1 `draft_supplier_email(supplier_name, supplier_contact, disruption_context, ask, sender_name, company_name)`

- **Purpose:** Draft supplier outreach email (never auto-sent).
- **Logic:** Template with subject, body (situation, ask, OEM commitments, reference SCR-YYYYMMDD-HHMM).
- **Output:** `draft_email` (to, subject, body, priority, draft_timestamp), `next_step`, `auto_send_eligible: false`, `reference_id`.

### 6.2 `send_slack_alert(channel, severity, disruption_summary, recommended_action, financial_exposure_usd, requires_approval)`

- **Purpose:** Format Slack alert (in production: Slack Web API).
- **Logic:** Severity emoji; build blocks (header, disruption, exposure, action, approval status, timestamp).
- **Output:** `channel`, `severity`, `message_preview`, `blocks`, `sent_at`, mock_note.

### 6.3 `flag_erp_reorder_adjustment(item_id, adjustment_type, new_quantity, reason, auto_execute=False)`

- **Purpose:** Flag or execute PO/reorder adjustment (in production: SAP/Oracle API).
- **Logic:** Build change record (change_id, item_id, adjustment_type, description, quantity, reason, status PENDING_APPROVAL or EXECUTED, created_at, created_by).
- **Output:** `erp_change`, `next_step`, mock_note.

### 6.4 `get_po_adjustment_suggestions()`

- **Purpose:** Restock suggestions from inventory vs reorder/target; mark auto-eligible if under threshold.
- **Logic:** Load action_config (auto_restock_threshold_usd, reorder_threshold_days, target_buffer_days, max_auto_restock_quantity_per_line). For each ERP inventory item: skip if days_on_hand >= target_days or (days_on_hand >= reorder_days and on_order > 0). shortfall_days = max(0, target_days - days_on_hand); suggested_qty = min(daily_consumption * shortfall_days, daily_consumption * (target_days+14)), at least daily_consumption*14. estimated_cost_usd = suggested_qty * unit_cost (from map); auto_eligible = cost <= threshold and qty <= max_auto_qty.
- **Output:** `suggestions[]` (item_id, description, suggested_quantity, reason, estimated_cost_usd, auto_eligible, days_on_hand, target_buffer_days), `auto_restock_threshold_usd`, `summary`.

### 6.5 `submit_restock_for_approval(item_id, suggested_quantity, reason, estimated_cost_usd, title)`

- **Purpose:** Create restock approval entry for human approval.
- **Logic:** Generate approval_id RST-YYYYMMDD-HHMMSS; build entry (type "restock", severity from cost, title, situation, recommendation, auditLog, status "pending", item_id, suggested_quantity, estimated_cost_usd, adjustment_reason); append to `ui/data/pending_approvals.json`.
- **Output:** `approval_id`, message, next_step (call execute_approved_restock after approval).

### 6.6 `execute_approved_restock(approval_id)`

- **Purpose:** Execute restock after human approval.
- **Logic:** Load pending_approvals; find entry by id; require type "restock" and status "approved"; call `flag_erp_reorder_adjustment(item_id, "emergency_po", suggested_quantity, reason, auto_execute=True)`; update entry status to "executed", set executed_at; save file.
- **Output:** `approval_id`, `erp_result`, message.

### 6.7 `escalate_to_management(trigger_reason, severity, problem_summary, decision_transparency_json, suggested_recipients)`

- **Purpose:** Escalate to management with decision transparency.
- **Logic:** Parse decision_transparency_json; filter keys by config `decision_transparency.include_in_escalation`; build record (id ESC-..., trigger_reason, severity, problem_summary, suggested_recipients, decision_transparency, created_at, status "pending_review"); append to `ui/data/escalations.json`.
- **Output:** `escalation_id`, `trigger_reason`, `suggested_recipients`, message.

### 6.8 `get_client_context()`

- **Purpose:** Client stance, sustainability, financial, legal, SCM inputs.
- **Logic:** Read action_config.client_context.
- **Output:** `client_context`, summary.

### 6.9 `get_workflow_integration_status()`

- **Purpose:** Status of ERP, Slack, email, WMS, TMS integrations.
- **Logic:** Read action_config.workflow_integrations; connected = keys where connected is true.
- **Output:** `integrations`, `connected_systems`, `one_stop_ui_summary`.

### 6.10 `submit_mitigation_for_approval(title, recommendation, situation, severity, context_summary, scenario_name, incremental_cost_usd)`

- **Purpose:** Add mitigation to Approval Inbox.
- **Logic:** approval_id APPR-YYYYMMDD-HHMMSS; build entry (severity, title, situation, recommendation, confidence, auditLog, status "pending"); append to `ui/data/pending_approvals.json`.
- **Output:** `approval_id`, message, next_step (user can approve/reject at /approvals).

### 6.11 `generate_executive_summary(disruption_event_json, risk_assessment_json, recommended_scenario_json, actions_taken_json)`

- **Purpose:** Formatted executive brief for leadership.
- **Logic:** Parse all four JSON inputs; build text with SITUATION (description, severity, regions), OPERATIONAL IMPACT (financial exposure, revenue at risk, SLA penalties, duration, affected lines), RECOMMENDED MITIGATION (scenario name, description, cost, service level, implementation days), ACTIONS INITIATED, DECISION REQUIRED.
- **Output:** `summary` (full text), `generated_at`, `severity`, `financial_exposure_usd`, `decision_deadline_hours`.

---

## 7. Reasoning log (stream)

**File:** `tools/reasoning_log.py`

- **Purpose:** Log every tool call and result for the agent stream (OBSERVE, MEMORY, REASONING, PLANNING, ACTION, RESULT); optional detail field for tool result JSON.
- **Logic:** `with_reasoning_log(func)` wraps each tool: optional delay (TOOL_CALL_DELAY_SECONDS); append_entry(domain_type, tool_call_string); flush(); run tool; append_entry("RESULT", summary, category, meta, detail=full result JSON); flush(). Domain mapping: perception_tools→OBSERVE, risk_tools/operational_impact_tools→REASONING, planning_tools→PLANNING, action_tools→ACTION, memory_tools→MEMORY.
- **Persistence:** `ui/data/agent_reasoning_stream.json`; API `GET /api/agent-stream` serves it to the UI.

---

## 8. Config and data paths (reference)

| Purpose | Default path | Env override |
|--------|---------------|--------------|
| Manufacturer profile | `config/manufacturer_profile.json` | MANUFACTURER_PROFILE_PATH |
| ERP snapshot | `data/mock_erp.json` | ERP_JSON_PATH |
| Active disruption (demo) | `config/active_disruption.json` | — |
| Disruption history | `data/mock_disruption_history.json` or project root / ui/data | — |
| Planning config | `planning_config.json` (project root) | PLANNING_CONFIG_PATH |
| Action config | `config/action_config.json` | ACTION_CONFIG_PATH |
| Risk model (optional) | `data/risk_model.joblib` + `data/risk_model_features.json` | — |
| Pending approvals | `ui/data/pending_approvals.json` | — |
| Escalations | `ui/data/escalations.json` | — |
| Planning documents | `ui/data/planning_documents.json` | — |
| Agent reasoning stream | `ui/data/agent_reasoning_stream.json` | — |

This completes the detailed reference for each agent, tool, and calculation used in the supply chain resilience system.
