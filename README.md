# Hack the Future 2026 - some supply chain agent something (name coming soon!)

helloww!

## Overview

- **Model:** Gemini 3.1 Flash Lite (default `gemini-3.1-flash-lite-preview`). Override with `GEMINI_MODEL`.

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

### Agent Reasoning Stream (dashboard UI)

The Next.js dashboard shows an **Agent Reasoning Stream** (OBSERVE, ACTION, RESULT, REASON, TOOL). The **orchestrator agent** fills this when it runs:

- **Run one cycle** (writes to `ui/data/agent_reasoning_stream.json`):
  ```bash
  python scripts/initiate_event.py --run
  ```
- **Run continuous detection** (each cycle overwrites the log):
  ```bash
  python scripts/run_continuous_detection.py --interval 0
  ```

Then refresh the dashboard or Disruptions page; they read from `/api/agent-stream`, which serves that file. Tools are wrapped to log **TOOL** (call) and **RESULT** (summary); model text is logged as **REASON**, **OBSERVE**, or **ACTION**.

**Rate limits (429):** Default model is `gemini-2.5-flash-lite` (10 requests/min free tier). Scripts retry up to 10 times on 429. Use `--interval 120` or higher. To space out tool calls and reduce burst load, set `TOOL_CALL_DELAY_SECONDS=2.5` (or 3) in `.env` or `orchestrator_agent/.env`. See [Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits).

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

- **1. Vicky Ongpipatanakul**
- **2. Punnawit Payapvattanavong**
- **3. Prima Limsuntrakul**
- **4. Lapatrada Jaroonjetjumnong**
- **5. Pera Kasemsripitak**
