# Hack the Future 2026 — Supply Chain Resilience Dashboard

Supply chain resilience dashboard for AutomotiveParts GmbH. A multi-agent AI system (Google ADK + Gemini) monitors supply chain disruptions and drives automated responses, with a Next.js dashboard as the UI.

## Overview

- **Model:** Gemini 2.5 Flash Lite (default `gemini-2.5-flash-lite`). Override with `GEMINI_MODEL`.

## Requirements

- **Python 3.12+**
- A [Google Cloud](https://cloud.google.com) project with Vertex AI / Gemini API enabled (for ADK/Gemini)
- **Node.js 18+** (for the Next.js frontend)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/clairelapatrada/htf26.git
cd htf26
```

### 2. Create a virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env` and fill in your API keys:

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Gemini API key |
| `GOOGLE_SEARCH_API_KEY` / `GOOGLE_SEARCH_ENGINE_ID` | Custom Search for perception tools |
| `NASA_API_KEY` | Climate/weather data |

### 5. Install frontend dependencies

```bash
cd frontend && npm install
```

## Running the app

**Backend** (port 8000):
```bash
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000
```

**Frontend** (port 3000):
```bash
cd frontend && npm run dev
```

### Agent Reasoning Stream (dashboard UI)

The Next.js dashboard shows an **Agent Reasoning Stream** (OBSERVE, ACTION, RESULT, REASON, TOOL). The **orchestrator agent** fills this when it runs:

- **Run one cycle:**
  ```bash
  python backend/scripts/initiate_event.py --run
  ```
- **Run continuous detection:**
  ```bash
  python backend/scripts/run_continuous_detection.py --interval 120
  ```

**Rate limits (429):** Default model is `gemini-2.5-flash-lite` (10 requests/min free tier). Use `--interval 120` or higher, and set `TOOL_CALL_DELAY_SECONDS=3` and `SUBAGENT_BREATHER_SECONDS=10` in `.env`. See [Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits).

## Disruption simulation

Everything is **OPERATIONAL** (no disruption) until you run **initiate**. The continuous detector will then report "all clear" until you turn on a disruption.

**Turn on a disruption** (Suez lane disrupted, supplier health degraded):
```bash
python backend/scripts/initiate_event.py
python backend/scripts/initiate_event.py --lane "Asia-Europe (Suez)" --delay-days 16
```

**Clear disruption** (back to all operational):
```bash
python backend/scripts/initiate_event.py --clear
```

**Continuous detection** (runs pipeline every N seconds):
```bash
python backend/scripts/run_continuous_detection.py
python backend/scripts/run_continuous_detection.py --interval 300
```

State is stored in `backend/config/active_disruption.json`. Run scripts from the project root.

## What each JSON file contains

| File | Purpose | Main keys / structure |
|------|--------|------------------------|
| **`backend/config/active_disruption.json`** | Controls whether perception reports a disruption. When `active` is false, all lanes are OPERATIONAL and supplier health is Stable. Set by `backend/scripts/initiate_event.py` and `--clear`. | `active` (bool), `supplier_health_degraded` (bool), `shipping_lanes` (object: lane name → `status`, `severity`, `avg_delay_days`, `reroute_*`, etc.). |
| **`backend/config/manufacturer_profile.json`** | Manufacturer and supply-chain master data used by risk and planning tools (and by perception for supplier context). | `suppliers` (id, name, category, country, spend_pct, lead_time_days, single_source, health_score, …), `inventory_policy` (target_buffer_days, reorder_threshold_days, max_buffer_days), `customer_slas` (customer, on_time_delivery_pct, penalty_per_day_usd), `production_lines` (line_id, product, semiconductor_dependent, daily_revenue_usd, …). |
| **`backend/data/mock_erp.json`** | Mock ERP snapshot: inventory and open purchase orders. Used by risk tools for runway, revenue-at-risk, and supplier exposure. | `inventory`: array of items (`item_id`, `description`, `supplier_id`, `days_on_hand`, `daily_consumption`, `stock_units`, `on_order_units`, `expected_delivery_date`). `open_purchase_orders`: array of POs (`po_id`, `supplier_id`, `value_usd`, `delivery_date`). |
| **`backend/planning_config.json`** | Scenario definitions, alternative suppliers, airfreight rates, and scoring weights for the planning tools. | `scenario_definitions`: airfreight, alternate_supplier, buffer_build, spot_market, demand_deferral (name, description, costs, implementation_days, service_level_protection, risks, co2_impact). `alternative_suppliers`: by category (e.g. Semiconductors, Plastic Injection Parts). `airfreight_rates`, `airfreight_defaults`. `risk_appetite_weights`, `service_level_scores`, `rank_service_scores`. |
| **`backend/data/mock_disruption_history.json`** | Log of past disruption events. Used by memory tools for similar-disruption retrieval and recurring patterns; new events appended by `log_disruption_event`. | Array of events: `event_id`, `date`, `type`, `region`, `severity`, `affected_suppliers`, `description`, `impact` (delay_days, revenue_at_risk_usd, actual_revenue_lost_usd), `mitigation_taken` (action, cost_usd, outcome), `lessons_learned`, optional `logged_by`, `logged_at`. |

## Our team

- **1. Vicky Ongpipatanakul**
- **2. Punnawit Payapvattanavong**
- **3. Prima Limsuntrakul**
- **4. Lapatrada Jaroonjetjumnong**
- **5. Pera Kasemsripitak**
