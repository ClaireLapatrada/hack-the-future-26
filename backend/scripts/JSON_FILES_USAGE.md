# JSON files — usage summary

Every JSON in the repo is **referenced** by code. Summary by file and who uses it.

| JSON file | Used by |
|-----------|--------|
| **config/active_disruption.json** | Python: `initiate_event.py`, `perception_tools`. Next: dashboard + disruptions API (parent path when cwd=ui). |
| **config/manufacturer_profile.json** | Python: `risk_tools`, `perception_tools`. Next: dashboard (when cwd=root or via parent path). |
| **config/rules.json** | Next: rules API (`config/rules.json` when cwd=project root). |
| **data/mock_erp.json** | Python: `risk_tools`. Next: dashboard, scenarios/run (when cwd=root or when they use `data/`). |
| **mock_disruption_history.json** (root) | Python: `memory_tools` (tries `data/` then root). Next: **never** — Next only reads `data/mock_disruption_history.json` (resolves to **ui/data/** when cwd=ui). |
| **planning_config.json** | Python: `planning_tools`. Next: scenarios/run, `GlobalDisruptionMap` (import from project root). |
| **ui/config/active_disruption.json** | Next: dashboard + disruptions API (local path when cwd=ui). |
| **ui/config/manufacturer_profile.json** | Next: dashboard when cwd=ui. |
| **ui/config/rules.json** | Next: rules API when cwd=ui. |
| **ui/data/agent_reasoning_stream.json** | Python: `reasoning_log` (writes). Next: agent-stream API (reads). |
| **ui/data/approval_resolutions.json** | Next: approvals API, dashboard (pending count). |
| **ui/data/mock_disruption_history.json** | Next: dashboard, approvals, disruptions APIs when cwd=ui. |
| **ui/data/mock_erp.json** | Next: dashboard when cwd=ui. |
| **ui/data/pending_approvals.json** | Python: `action_tools` (writes). Next: approvals API, dashboard (pending count). |

**Build/config (always used):**  
`ui/tsconfig.json`, `ui/package.json`, `ui/package-lock.json` — tooling/npm.

---

## Not used / redundant

- **Root `mock_disruption_history.json`** — Only used by **Python** (`memory_tools`). The **Next.js** app (when run from `ui/`) only reads **`ui/data/mock_disruption_history.json`**. So the root copy is not used by the UI; it’s only for the agent. If you run the UI from project root, `data/mock_disruption_history.json` would be used (root `data/`), and the root `mock_disruption_history.json` would still only be used by Python.
- **`data/agent_reasoning_stream_disruption.json`** and **`data/agent_reasoning_stream_disruption_<eventId>.json`** — Optional paths in the agent-stream API; no such files exist in the repo. So there are no unused JSON files for these; they’re optional overrides.
- **Duplicate config/data** — `config/` vs `ui/config/` and `data/` vs `ui/data/` exist for different run contexts (Python vs Next, or Next from root vs from `ui/`). Both sides are used depending on how you run the app.

**Bottom line:** There are **no JSON files that are never used**. The root **`mock_disruption_history.json`** is only used by Python (memory tools); the UI uses **`ui/data/mock_disruption_history.json`** when running from `ui/`. You could remove the root copy only if you don’t use the Python memory tools or you point them at `ui/data/mock_disruption_history.json` (or another single source).
