# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Supply chain resilience agent system for "AutomotiveParts GmbH". A Python multi-agent backend (Google ADK + Gemini) paired with a Next.js dashboard UI.

## Development Commands

### Python Backend

```bash
# Activate virtualenv (Python 3.12, located at .venv/)
source .venv/bin/activate

# Install Python deps
pip install -r requirements.txt

# Run agent interactively via ADK
adk run orchestrator_agent

# Trigger a disruption event and run one pipeline cycle
python scripts/initiate_event.py --lane "Asia-Europe (Suez)" --delay-days 16
python scripts/initiate_event.py --run   # run detection with current state

# Clear all disruptions (back to OPERATIONAL)
python scripts/initiate_event.py --clear

# Run continuous detection loop
python scripts/run_continuous_detection.py --interval 300   # every 5 min
python scripts/run_continuous_detection.py --interval 0    # once and exit
```

### Next.js Frontend (run from `ui/`, not project root)

```bash
cd ui
npm install    # first time only
npm run dev
npm run build
npm run lint
```

The root `package.json` is a stub and does **not** contain Next.js. Always `cd ui` first.

### Google Cloud Auth

```bash
gcloud auth application-default login
```

## Architecture

### Two Runtime Modes

**Sub-agent mode (default):** `orchestrator_agent/agent.py` — the root orchestrator has five sub-agents registered as tools via `DelayedAgentTool`. The orchestrator calls them in sequence: `perception_agent → memory_agent → risk_agent → planning_agent → action_agent`. Each sub-agent has its own `agent.py` under its directory.

**Flat mode:** `orchestrator_agent/agent_flat.py` — single root agent with all tools registered directly. Enable with `ORCHESTRATOR_USE_FLAT=1`. Use when sub-agent mode hits "Tool use with function calling is unsupported" or to reduce API round-trips.

### Pipeline Steps (PERCEIVE → MEMORY → RISK → PLAN → ACTION → LOG)

| Step | Sub-agent | Key tools |
|------|-----------|-----------|
| 1 PERCEIVE | `perception_agent/` | `search_disruption_news`, `get_shipping_lane_status`, `get_climate_alerts`, `score_supplier_health` |
| 2 MEMORY | `memory_agent/` | `retrieve_similar_disruptions`, `get_recurring_risk_patterns` |
| 3 RISK | `risk_agent/` | `get_disruption_probability`, `get_supplier_exposure`, `get_inventory_runway`, `calculate_revenue_at_risk` |
| 4 PLAN | `planning_agent/` | `simulate_mitigation_scenario`, `rank_scenarios`, `create_planning_document` |
| 5 ACTION | `action_agent/` | `send_slack_alert`, `draft_supplier_email`, `submit_restock_for_approval`, `escalate_to_management` |
| 6 LOG | (orchestrator) | `log_disruption_event` |

All tool calls are wrapped by `tools/reasoning_log.py` (`with_reasoning_log`) which appends every call/result to `ui/data/agent_reasoning_stream.json`.

### Tool Modules (`tools/`)

- `perception_tools.py` — news search, shipping lane status, climate alerts, supplier health scoring
- `risk_tools.py` — probability, exposure, inventory runway, revenue-at-risk, SLA breach
- `planning_tools.py` — scenario simulation, alternative suppliers, airfreight estimates, planning docs
- `action_tools.py` — PO adjustments, approvals, Slack, email drafts, ERP flags, escalation
- `memory_tools.py` — disruption history retrieval, recurring patterns
- `operational_impact_tools.py` — operational impact calculations
- `reasoning_log.py` — wraps tools to stream reasoning to UI
- `delayed_agent_tool.py` — `DelayedAgentTool` wrapper for sub-agents with rate-limit delay
- `rate_limiter.py` — retry logic for Gemini 429 errors

### Next.js UI (`ui/`)

Next.js 14 App Router. Pages: dashboard, disruptions, approvals. API routes under `ui/app/api/` read JSON files from `ui/data/` and `ui/config/`. The frontend never calls the Python backend directly — it reads JSON files that Python writes.

**Key API routes:**
- `/api/agent-stream` — serves `ui/data/agent_reasoning_stream.json`
- `/api/approvals` — reads/writes `ui/data/pending_approvals.json`
- `/api/planning-documents` — reads `ui/data/planning_documents.json`
- `/api/dashboard` — aggregates ERP, disruption, approvals data

### Data & Config Files

Python reads from project root paths; Next.js reads from `ui/` paths when run from `ui/`. Both sets of files must be kept in sync when making changes.

| File | Purpose |
|------|---------|
| `config/active_disruption.json` | Controls whether perception reports a disruption |
| `config/manufacturer_profile.json` | Supplier master data, SLAs, production lines |
| `data/mock_erp.json` | Inventory snapshot and open POs |
| `planning_config.json` | Scenario definitions, alt suppliers, airfreight rates |
| `mock_disruption_history.json` | Past events (Python only; UI reads `ui/data/` copy) |
| `ui/data/agent_reasoning_stream.json` | Realtime reasoning log written by Python, read by UI |
| `ui/data/pending_approvals.json` | Written by `action_tools`, read by approvals UI |

### Environment Variables

Set in `.env` at project root or `orchestrator_agent/.env`:

| Variable | Purpose |
|----------|---------|
| `GEMINI_MODEL` | Override model (default: `gemini-2.5-flash-lite`) |
| `ORCHESTRATOR_USE_FLAT` | Set to `1` for flat agent mode |
| `ORCHESTRATOR_SUBAGENTS` | Comma-separated subset of sub-agents to enable, or `all`/`none` |
| `SUBAGENT_BREATHER_SECONDS` | Delay between sub-agent calls (default: 10) |
| `TOOL_CALL_DELAY_SECONDS` | Delay between tool calls to reduce 429s (e.g. `2.5`) |
| `GOOGLE_CLOUD_PROJECT` | GCP project for Vertex AI / Gemini |

**Rate limits:** Free tier is 10 req/min. Use `--interval 120` or set `TOOL_CALL_DELAY_SECONDS=3` in `.env` if hitting 429s. Scripts retry up to 10 times on 429.