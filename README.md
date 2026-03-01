# Hack the Future 2026 - some supply chain agent something (name coming soon!)

helloww!

## Overview

- **Model:** Gemini 2.5 Flash.

## Requirements

- **Python 3.11+**
- A [Google Cloud](https://cloud.google.com) project with Vertex AI / Gemini API enabled (for ADK/Gemini)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/clairelapatrada/htf26.git
cd htf26
```

### 2. Create a virtual environment (recommended)

Using Python 3.11:

```bash
python3.11 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
```

If `python3.11` isn’t in your PATH, use the full path (e.g. `/opt/homebrew/bin/python3.11` on macOS with Homebrew).

### 3. Install dependencies

Install the Agent Development Kit and its dependencies:

```bash
pip install --upgrade pip
pip install "google-adk>=1.18"
```

Optional: to install from the pinned list (may need version tweaks for your Python):

```bash
pip install -r requirements.txt
```

### 4. Configure Google Cloud authentication

Set up Application Default Credentials so the agent can call Gemini:

```bash
gcloud auth application-default login
```

Or set `GOOGLE_CLOUD_PROJECT` and use a service account key as needed for your environment.

## Running the agent

With the virtual environment activated:

```bash
adk run my_agent
```

```bash
python -c "from my_agent.agent import root_agent; print(root_agent.name)"
```

## Suggested features — implementation status

Legend: **✅ Finished (real)** = live API or real integration | **✅ Finished (mock)** = implemented with mock data/config | **❌ Not implemented**

### 1. Perception Layer

| Feature | Status | Notes |
|--------|--------|--------|
| News ingestion module | ✅ Finished (real) | `search_disruption_news` — Google Custom Search when `GOOGLE_SEARCH_*` set; else error, no mock |
| Supply risk classification | ⚠️ Partial | LLM classifies from news/signals; no dedicated classifier module |
| ERP signal monitoring | ✅ Finished (mock) | Risk tools read `data/mock_erp.json` (inventory, open POs); no live ERP |
| Supplier health scoring | ✅ Finished (real/mock) | `score_supplier_health` — Gemini when disruption initiated; else canned “Stable” from `config/active_disruption.json` |
| Shipping lane status | ✅ Finished (mock) | `get_shipping_lane_status` — reads `config/active_disruption.json`; initiate/clear to toggle |
| Climate alerts | ✅ Finished (real) | `get_climate_alerts` — NASA EONET (optional `NASA_API_KEY`) |

### 2. Risk Intelligence Engine

| Feature | Status | Notes |
|--------|--------|--------|
| Disruption probability scoring | ⚠️ Partial | `calculate_sla_breach_probability` uses a simple formula; no full probabilistic model |
| Operational impact modeling | ✅ Finished (mock) | `calculate_revenue_at_risk`, `get_supplier_exposure`, `get_inventory_runway` — use `mock_erp.json` + `config/manufacturer_profile.json` |
| Revenue-at-risk estimation | ✅ Finished (mock) | `calculate_revenue_at_risk` — production lines, SLAs, inventory from config |
| Multi-variable trade-off simulation | ✅ Finished (mock) | `rank_scenarios` — cost/service/speed from `planning_config.json` |

### 3. Planning & Decision Engine

| Feature | Status | Notes |
|--------|--------|--------|
| Scenario simulation (cost vs service) | ✅ Finished (mock) | `simulate_mitigation_scenario` — airfreight, buffer_build, alternate_supplier, etc. from `planning_config.json` |
| Supplier reallocation optimization | ✅ Finished (mock) | `get_alternative_suppliers` — list from config (e.g. ChipWorks Korea, EuroSemi); no optimization solver |
| Buffer stock strategy modeling | ✅ Finished (mock) | “buffer_build” scenario in config; inventory policy in manufacturer_profile |
| Decision tree reasoning | ✅ Finished (mock) | Orchestrator LLM + `rank_scenarios`; no explicit decision tree structure |
| Airfreight rate estimate | ✅ Finished (mock) | `get_airfreight_rate_estimate` — rates from `planning_config.json` |

### 4. Autonomous Action Layer

| Feature | Status | Notes |
|--------|--------|--------|
| Auto-generated supplier emails | ✅ Finished (mock) | `draft_supplier_email` — generates draft; never auto-sends (instruction: human approval) |
| Purchase order adjustment suggestions | ✅ Finished (mock) | `flag_erp_reorder_adjustment` — returns “mock_note”; no SAP/Oracle integration |
| Escalation triggers | ✅ Finished (mock) | `send_slack_alert` — returns success + mock_note; no real Slack API |
| Executive summary | ✅ Finished (mock) | `generate_executive_summary` — builds summary from JSON inputs; no workflow integration |
| Workflow integrations | ❌ Not implemented | No Gmail, Slack, or ERP APIs wired |

### 5. Memory & Reflection System

| Feature | Status | Notes |
|--------|--------|--------|
| Logs past disruptions | ✅ Finished (mock) | `log_disruption_event` — appends to `mock_disruption_history.json` (or Qdrant if configured) |
| Evaluates mitigation success | ⚠️ Partial | History stores outcome; `retrieve_similar_disruptions` surfaces past cases; no formal “success score” |
| Improves future recommendations | ⚠️ Partial | LLM uses memory context in pipeline; no explicit learning loop or model update |
| Similar-disruption retrieval | ✅ Finished (mock/real) | `retrieve_similar_disruptions` — keyword or Qdrant embeddings when `QDRANT_URL` + `GEMINI_API_KEY` set |
| Recurring risk patterns | ✅ Finished (mock) | `get_recurring_risk_patterns` — derived from history; no external pattern DB |

### 6. Decision Transparency

| Feature | Status | Notes |
|--------|--------|--------|
| Explainable reasoning traces | ⚠️ Partial | Final “Supply Chain Operations Briefing” includes reasoning; no step-by-step trace UI |
| Risk justification logic | ⚠️ Partial | Briefing explains threat level and recommendation; logic in prompt + tool outputs |
| Human override thresholds | ✅ Finished (doc only) | In orchestrator instruction: e.g. ERP > $50K → procurement approval; spend > $150K → CFO; emails never auto-sent |
| Bias and constraint validation | ❌ Not implemented | No formal bias checks or constraint validation layer |

---

## Continuous detection and initiate event

Everything is **OPERATIONAL** (no disruption) until you run **initiate**. The continuous detector will then report "all clear" until you turn on a disruption.

**Turn on a disruption** (Suez lane disrupted, supplier health degraded — next detection run will see it):
```bash
python scripts/initiate_event.py
python scripts/initiate_event.py --lane "Asia-Europe (Suez)" --delay-days 16
```

**Clear disruption** (back to all operational):
```bash
python scripts/initiate_event.py --clear
```

**Run one detection cycle** (with current state: disrupted if you initiated, else operational):
```bash
python scripts/initiate_event.py --run
```

**Continuous detection** (runs pipeline every N seconds, prints briefing and takes actions):
```bash
python scripts/run_continuous_detection.py
python scripts/run_continuous_detection.py --interval 300   # every 5 min
python scripts/run_continuous_detection.py --interval 0    # run once and exit
```

State is stored in `config/active_disruption.json`. Run scripts from the project root.

## What each JSON file contains

| File | Purpose | Main keys / structure |
|------|--------|------------------------|
| **`config/active_disruption.json`** | Controls whether perception reports a disruption. When `active` is false, all lanes are OPERATIONAL and supplier health is Stable. Set by `scripts/initiate_event.py` and `--clear`. | `active` (bool), `supplier_health_degraded` (bool), `shipping_lanes` (object: lane name → `status`, `severity`, `avg_delay_days`, `reroute_*`, etc.). |
| **`config/manufacturer_profile.json`** | Manufacturer and supply-chain master data used by risk and planning tools (and by perception for supplier context). | `suppliers` (id, name, category, country, spend_pct, lead_time_days, single_source, health_score, …), `inventory_policy` (target_buffer_days, reorder_threshold_days, max_buffer_days), `customer_slas` (customer, on_time_delivery_pct, penalty_per_day_usd), `production_lines` (line_id, product, semiconductor_dependent, daily_revenue_usd, …). |
| **`data/mock_erp.json`** | Mock ERP snapshot: inventory and open purchase orders. Used by risk tools for runway, revenue-at-risk, and supplier exposure. | `inventory`: array of items (`item_id`, `description`, `supplier_id`, `days_on_hand`, `daily_consumption`, `stock_units`, `on_order_units`, `expected_delivery_date`). `open_purchase_orders`: array of POs (`po_id`, `supplier_id`, `value_usd`, `delivery_date`). |
| **`planning_config.json`** | Scenario definitions, alternative suppliers, airfreight rates, and scoring weights for the planning tools. | `scenario_definitions`: airfreight, alternate_supplier, buffer_build, spot_market, demand_deferral (name, description, costs, implementation_days, service_level_protection, risks, co2_impact). `alternative_suppliers`: by category (e.g. Semiconductors, Plastic Injection Parts). `airfreight_rates`, `airfreight_defaults`. `risk_appetite_weights`, `service_level_scores`, `rank_service_scores`. |
| **`mock_disruption_history.json`** | Log of past disruption events. Used by memory tools for similar-disruption retrieval and recurring patterns; new events appended by `log_disruption_event`. Can live in project root or `data/`. | Array of events: `event_id`, `date`, `type`, `region`, `severity`, `affected_suppliers`, `description`, `impact` (delay_days, revenue_at_risk_usd, actual_revenue_lost_usd), `mitigation_taken` (action, cost_usd, outcome), `lessons_learned`, optional `logged_by`, `logged_at`. |

## Our team

- **1. Vicky Ongpipatanakul** — role
- **2. Punnawit Payapvattanavong** — role
- **3. Prima Limsuntrakul** — role
- **4. Lapatrada Jaroonjetjumnong** — role
- **5. Pera Kasemsripitak** — role
