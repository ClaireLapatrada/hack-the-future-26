# Integration options for the supply chain resilience agent

This doc maps **Goodmem**, **MCP toolbox for databases**, **Qdrant**, **Supermetrics**, and related tools to the htf26 pipeline. **Qdrant** and **Goodmem** are implemented; the rest are optional.

---

## Implemented

### Qdrant (Memory agent — semantic similar disruptions)

**Status:** Implemented in `tools/memory_tools.py`.

- **retrieve_similar_disruptions:** When `QDRANT_URL` and `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) are set, uses Gemini embeddings and Qdrant for semantic search. Otherwise falls back to keyword matching over JSON.
- **log_disruption_event:** Appends to JSON and, when Qdrant is configured, upserts the new event into the `disruption_events` collection.
- **Backfill:** On first semantic search, if the collection is empty, events from `mock_disruption_history.json` are embedded and indexed.

**Setup:**

1. Run Qdrant (e.g. Docker): `docker run -p 6333:6333 qdrant/qdrant`
2. In `.env` or `memory_agent/.env`:
   ```
   QDRANT_URL=http://localhost:6333
   GEMINI_API_KEY=your_gemini_key
   ```
3. Install: `pip install qdrant-client` (already in `requirements.txt`).

**Env vars:** `QDRANT_URL` (or `QDRANT_HOST`), `GEMINI_API_KEY` or `GOOGLE_API_KEY`.

---

### Goodmem (Orchestrator — persistent session memory)

**Status:** Implemented in `orchestrator_agent/agent.py`.

- When `GOODMEM_BASE_URL` and `GOODMEM_API_KEY` are set, the orchestrator gets **goodmem_save** and **goodmem_fetch** tools. The agent can recall past decisions, user preferences, and escalation outcomes across runs.
- Goodmem requires a [GoodMem instance](https://goodmem.ai/quick-start) (self-hosted or cloud) and a GoodMem API key. Gemini is used for embeddings (set `GOOGLE_API_KEY` for the Goodmem plugin).

**Setup:**

1. Create an account and instance at [goodmem.ai](https://goodmem.ai/).
2. In `.env` or `orchestrator_agent/.env`:
   ```
   GOODMEM_BASE_URL=https://your-instance.goodmem.ai
   GOODMEM_API_KEY=your_goodmem_key
   GOOGLE_API_KEY=your_gemini_key
   ```
3. Install: `pip install goodmem-adk` (already in `requirements.txt`).

**Env vars:** `GOODMEM_BASE_URL`, `GOODMEM_API_KEY`, `GOOGLE_API_KEY` (for embeddings).

---

## 1. **Qdrant** (vector database) — **High value**

**What it is:** Vector DB for semantic search and RAG.

**Where it fits in this project:**

| Agent / flow | Current state | With Qdrant |
|--------------|----------------|-------------|
| **Memory** — `retrieve_similar_disruptions` | Keyword-style match over `mock_disruption_history.json` | Embed disruption descriptions + type/region; semantic similarity over past events. Better “similar past case” retrieval. |
| **Memory** — `log_disruption_event` | Append to JSON | Persist event and upsert embedding into Qdrant for future similarity search. |
| **Planning / Risk** | Static config + profile | Optional: RAG over playbooks, supplier docs, or mitigation templates stored as chunks in Qdrant. |

**Why use it:** The Memory agent’s “in production: Vertex AI Vector Search” is exactly this use case. Qdrant is a straightforward way to get semantic “find similar disruptions” and “find similar mitigations” without full Vertex setup.

**Implementation sketch:** Embed each disruption (e.g. description + type + region) with Gemini or another embedder; store in Qdrant. In `retrieve_similar_disruptions`, embed the query and run a vector search; return top-k. Optionally keep writing to JSON for backup or migrate fully to Qdrant + your DB.

---

## 2. **MCP toolbox for databases** — **High value**

**What it is:** MCP (Model Context Protocol) tools that let an agent query and, where supported, write to databases (Postgres, MySQL, BigQuery, etc.).

**Where it fits in this project:**

| Agent / flow | Current state | With MCP DB tools |
|--------------|----------------|--------------------|
| **Memory** | Read/write `mock_disruption_history.json` | Read/write a `disruptions` (or similar) table; `log_disruption_event` inserts; `retrieve_similar_disruptions` and `get_recurring_risk_patterns` become SQL or MCP-backed queries. |
| **Risk** | `_load_profile()`, `_load_erp()` from JSON files | Load manufacturer profile and ERP-style data from real tables (e.g. `suppliers`, `inventory`, `production_lines`). |
| **Planning** | `planning_config.json` | Optional: scenario definitions, alternative suppliers, rates in DB so ops can change them without editing JSON. |

**Why use it:** You already have a clear “in production: Firestore / DB” story. MCP DB tools let the same agents work against a real database (and optionally keep JSON for local/dev). Good next step after (or alongside) Qdrant for Memory.

**Implementation sketch:** Add an MCP server that exposes your DB (e.g. Postgres or BigQuery). Register it with the ADK/orchestrator. Memory/Risk tools either call MCP for reads/writes or you replace their internals with DB client calls that mirror the current tool contracts.

---

## 3. **Goodmem (e.g. Goldfish Memory / agent memory)** — **Medium value**

**What it is:** Persistent memory for agents (conversation history, learned facts, user preferences).

**Where it fits in this project:**

| Agent / flow | Use case |
|--------------|----------|
| **Orchestrator** | Remember “user asked to prioritize SUP-001” or “last run we escalated to CFO”; carry context across sessions. |
| **Memory agent** | Optional: user-level or tenant-level “remember my risk appetite” or “remember which suppliers I care about most.” |
| **Any agent** | “Don’t repeat the same recommendation you gave last week” or “remember the chosen mitigation so we can track outcome.” |

**Why use it:** Today the pipeline is largely stateless per run. Goodmem-style memory gives you cross-session continuity and more personalized behavior without building your own store.

**Implementation sketch:** Integrate the memory service with the orchestrator (or session layer). Before/after runs, read/write “user memory” or “session summary” so the next run can reference it in the system prompt or tool context.

---

## 4. **Supermetrics (Google tools)** — **Niche**

**What it is:** Pulls data from Google products (Analytics, Ads, Search Console, Sheets, etc.) into one place (often for reporting/BI).

**Where it could fit:**

| Use case | When it’s useful |
|----------|-------------------|
| **Supplier / logistics metrics in Sheets** | If you keep supplier scorecards, delivery KPIs, or risk registers in Google Sheets, Supermetrics can pipe that into a DB or API the agent reads (e.g. via MCP or a small ETL). |
| **Google Analytics / Ads** | Only relevant if you treat “demand” or “campaign” data as a supply chain signal (e.g. demand spike → inventory risk). |

**Why it’s niche:** Your current signals are news (Google CSE), climate (NASA), supplier health (Gemini), and internal profile/ERP. Supermetrics adds value only if you introduce Google-sourced datasets (e.g. Sheets-based supplier list or KPI dashboard) as an input to Perception or Risk.

**Implementation sketch:** Use Supermetrics to sync Sheets (or other Google data) into a table or file; then have Perception or Risk tools (or MCP DB) read that table.

---

## 5. **Other Google tools** (beyond CSE + Gemini)

Already in use or documented: **Google Custom Search**, **Gemini**, **google_search (ADK)**. Additional options:

- **BigQuery:** If disruption events, supplier data, or ERP-style data live in BigQuery, use MCP for BigQuery or direct client in Memory/Risk tools.
- **Sheets API:** Read/write supplier lists, runways, or simple config from Sheets (e.g. for Risk or Planning) without Supermetrics if you prefer direct API.
- **Drive:** Store and retrieve playbooks, contracts, or reports for RAG (e.g. in Qdrant after chunking).

---

## Suggested priority for this project

1. **Qdrant** — Improves Memory’s “similar past disruptions” and “similar mitigations” with minimal change to tool interfaces.
2. **MCP toolbox for databases** — Unlocks real profile/ERP and disruption storage; aligns with your “production: Firestore/DB” comments.
3. **Goodmem (agent memory)** — Add once you want cross-session behavior and personalized orchestration.
4. **Supermetrics / more Google** — Add only if you introduce Google Sheets (or similar) as a first-class data source for the pipeline.

If you tell me which of these you want to implement first (e.g. “Qdrant for Memory” or “MCP for Postgres”), I can outline concrete steps and code changes in this repo.
