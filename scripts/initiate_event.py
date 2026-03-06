#!/usr/bin/env python3
"""
Initiate a disruption (turn on Suez + supplier risk) or clear it, then optionally run one detection cycle.

Everything is OPERATIONAL until you run "initiate". After that, the next detection run
will see the disruption (Suez lane disrupted, supplier health degraded).

  Turn on disruption (Suez 16-day delay, supplier health degraded):
    python scripts/initiate_event.py
    python scripts/initiate_event.py --lane "Asia-Europe (Suez)" --delay-days 16

  Run one detection cycle (with current state: disrupted if you initiated, else operational):
    python scripts/initiate_event.py --run

  On 429 rate limit (Gemini free tier: 5 req/min), the script waits and retries once.

  Clear disruption (back to all operational):
    python scripts/initiate_event.py --clear

Run from project root. Env vars from orchestrator_agent/.env and root .env.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(PROJECT_ROOT / "orchestrator_agent" / ".env")
except ImportError:
    pass

CONFIG_PATH = PROJECT_ROOT / "config" / "active_disruption.json"

# Default disruption payload when you "initiate" (Suez disrupted)
DEFAULT_LANE_OVERRIDE = {
    "Asia-Europe (Suez)": {
        "status": "DISRUPTED",
        "severity": "High",
        "avg_delay_days": 16,
        "reroute_available": True,
        "reroute_via": "Cape of Good Hope",
        "reroute_additional_days": 14,
        "carrier_surcharges_usd_per_teu": 2800,
        "vessels_affected_pct": 68,
    }
}


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {"active": False, "supplier_health_degraded": False, "shipping_lanes": {}}
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_config(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def set_disruption_active(lane: str, delay_days: int) -> None:
    """Set config so perception reports a disruption (Suez lane + supplier health degraded)."""
    overrides = {
        lane: {
            "status": "DISRUPTED",
            "severity": "High",
            "avg_delay_days": delay_days,
            "reroute_available": True,
            "reroute_via": "Cape of Good Hope",
            "reroute_additional_days": 14,
            "carrier_surcharges_usd_per_teu": 2800,
            "vessels_affected_pct": 68,
        }
    }
    data = _load_config()
    data["active"] = True
    data["supplier_health_degraded"] = True
    data["shipping_lanes"] = overrides
    _save_config(data)
    print(f"Disruption initiated: {lane} DISRUPTED, {delay_days} day(s) delay. Supplier health set to degraded.")
    print(f"Config written to {CONFIG_PATH}")


def clear_disruption() -> None:
    """Set config so all lanes and supplier health are operational."""
    data = {"active": False, "supplier_health_degraded": False, "shipping_lanes": {}}
    _save_config(data)
    print("Disruption cleared. All lanes and supplier health are OPERATIONAL.")
    print(f"Config written to {CONFIG_PATH}")


def _is_rate_limit_error(e: BaseException) -> bool:
    s = str(e).upper()
    return "429" in s or "RESOURCE_EXHAUSTED" in s


def _extract_retry_seconds(e: BaseException) -> int:
    import re
    m = re.search(r"retry in (\d+(?:\.\d+)?)\s*s", str(e), re.I)
    if m:
        return min(120, max(10, int(float(m.group(1)) + 1)))
    return 55


def _run_one_cycle(prompt: str) -> None:
    """Run one detection cycle using the same runner as run_continuous_detection. Writes reasoning stream to ui/data/agent_reasoning_stream.json."""
    from contextlib import aclosing
    from google.genai import types
    from google.adk.apps.app import App
    from google.adk.runners import Runner
    from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
    from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
    from tools.reasoning_log import append_entry, flush, clear as clear_reasoning_log
    import importlib.util

    def _classify(text: str) -> tuple[str, str | None]:
        t = text.strip().lower()
        if ("approval" in t and "request" in t) or ("generating" in t and "request" in t):
            return "ACTION", None
        if t.startswith("monitoring") or "monitoring " in t or "evaluating " in t:
            return "OBSERVE", None
        import re
        m = re.search(r"(\d{1,3})%", text)
        return "REASON", f"{m.group(1)}%" if m else None

    clear_reasoning_log()
    agent_path = PROJECT_ROOT / "orchestrator_agent" / "agent.py"
    spec = importlib.util.spec_from_file_location("orchestrator_agent.agent", agent_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("orchestrator_agent", type(sys)("orchestrator_agent"))
    sys.modules["orchestrator_agent.agent"] = mod
    spec.loader.exec_module(mod)
    agent = getattr(mod, "root_agent")

    app = App(name="orchestrator_agent", root_agent=agent)
    session_service = InMemorySessionService()

    async def _run():
        session = await session_service.create_session(
            app_name="orchestrator_agent", user_id="initiate_event"
        )
        runner = Runner(
            app=app,
            artifact_service=InMemoryArtifactService(),
            session_service=session_service,
            memory_service=InMemoryMemoryService(),
            credential_service=InMemoryCredentialService(),
        )
        content = types.Content(role="user", parts=[types.Part(text=prompt)])
        async with aclosing(
            runner.run_async(user_id=session.user_id, session_id=session.id, new_message=content)
        ) as agen:
            async for event in agen:
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        text = getattr(part, "text", None)
                        if text and text.strip():
                            entry_type, confidence = _classify(text)
                            append_entry(entry_type, text.strip(), confidence=confidence)
                            flush()
                    text = "".join(getattr(p, "text", None) or "" for p in event.content.parts)
                    if text:
                        print(f"[{event.author or 'agent'}]:")
                        print(text)
                        print()
        await runner.close()

    try:
        asyncio.run(_run())
    except Exception as e:
        if not _is_rate_limit_error(e):
            raise
        for attempt in range(1, 4):
            wait_s = _extract_retry_seconds(e)
            print(f"[429] Rate limit. Waiting {wait_s}s (retry {attempt}/3)...", file=sys.stderr)
            import time
            time.sleep(wait_s)
            try:
                asyncio.run(_run())
                return
            except Exception as e2:
                e = e2
                if not _is_rate_limit_error(e2):
                    raise
        print(f"[error] Still rate limited after 3 retries. Wait 1 min or enable billing.", file=sys.stderr)
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Initiate or clear disruption state; optionally run one detection cycle."
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run one detection cycle and print the briefing (does not change disruption state).",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear disruption: set all lanes and supplier health to OPERATIONAL/Stable.",
    )
    parser.add_argument(
        "--lane",
        type=str,
        default="Asia-Europe (Suez)",
        help="Lane to mark DISRUPTED when initiating (default: Asia-Europe (Suez)).",
    )
    parser.add_argument(
        "--delay-days",
        type=int,
        default=16,
        help="Average delay in days for the initiated lane (default: 16).",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default="Check for any disruption. Run the full pipeline and output the Supply Chain Operations Briefing.",
        help="Prompt when using --run.",
    )
    args = parser.parse_args()

    if args.clear:
        clear_disruption()
        return
    if args.run:
        _run_one_cycle(prompt=args.prompt)
        return
    # Default: initiate disruption (turn on Suez + supplier health degraded)
    set_disruption_active(lane=args.lane, delay_days=args.delay_days)


if __name__ == "__main__":
    main()
