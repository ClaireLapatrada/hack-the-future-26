#!/usr/bin/env python3
"""
Continuous supply chain detection — runs the orchestrator agent in a loop
without waiting for user input. Each cycle: run full pipeline, print briefing,
take actions, then sleep and repeat.

Run from project root:
  python scripts/run_continuous_detection.py
  python scripts/run_continuous_detection.py --interval 300   # 5 min

By default uses SUB-AGENTS (orchestrator_agent/agent.py). Set ORCHESTRATOR_USE_FLAT=1
to use the flat orchestrator (one agent, all tools) instead.

Env: GEMINI_MODEL, TOOL_CALL_DELAY_SECONDS (default 6), STARTUP_DELAY_SECONDS (default 15 for sub-agents).
If you hit 429 with sub-agents, try STARTUP_DELAY_SECONDS=20 and TOOL_CALL_DELAY_SECONDS=8.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Project root = parent of scripts/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load .env before importing agent (tools load their own)
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(PROJECT_ROOT / "orchestrator_agent" / ".env")
except ImportError:
    pass

from contextlib import aclosing
from google.genai import types
from google.adk.apps.app import App
from google.adk.runners import Runner
from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService

from tools.reasoning_log import append_entry, flush, clear as clear_reasoning_log


# Resolved model (after .env) — log so user can confirm 3.1 vs 2.5
_RESOLVED_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")


# Default prompt for each detection cycle
DEFAULT_PROMPT = (
    "Check for any disruption. Run the full pipeline: "
    "perceive (news, shipping lanes, climate, supplier health), "
    "memory (similar disruptions, patterns), "
    "risk (exposure, inventory runway, SLA), "
    "plan (scenarios, rank), "
    "action (Slack, draft email, ERP flag, executive summary), "
    "and log. Output the Supply Chain Operations Briefing at the end."
)


def _load_agent():
    """Load orchestrator. Default: sub-agents (agent.py). Set ORCHESTRATOR_USE_FLAT=1 for flat/tools-only."""
    use_flat = os.environ.get("ORCHESTRATOR_USE_FLAT", "0").strip().lower() in ("1", "true", "yes")
    module_name = "orchestrator_agent.agent_flat" if use_flat else "orchestrator_agent.agent"
    agent_file = "agent_flat.py" if use_flat else "agent.py"
    agent_path = PROJECT_ROOT / "orchestrator_agent" / agent_file
    import importlib.util
    spec = importlib.util.spec_from_file_location(module_name, agent_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["orchestrator_agent"] = type(sys)("orchestrator_agent")
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return getattr(mod, "root_agent")


def _classify_model_text(text: str) -> tuple[str, str | None]:
    """Return (entry_type, confidence). Types: OBSERVE, ACTION, REASON."""
    t = text.strip().lower()
    if ("approval" in t and "request" in t) or ("generating" in t and "request" in t):
        return "ACTION", None
    if t.startswith("monitoring") or "monitoring " in t or "evaluating " in t:
        return "OBSERVE", None
    # Optional: extract confidence like "87%" for REASON
    import re
    m = re.search(r"(\d{1,3})%", text)
    conf = f"{m.group(1)}%" if m else None
    return "REASON", conf


def _print_event(event):
    """Print agent response text from an event and append to reasoning log for UI."""
    if not event.content or not event.content.parts:
        return
    for part in event.content.parts:
        text = getattr(part, "text", None)
        if not text or not text.strip():
            continue
        entry_type, confidence = _classify_model_text(text)
        append_entry(entry_type, text.strip(), confidence=confidence)
        flush()
    text_parts = [p.text for p in event.content.parts if getattr(p, "text", None)]
    if not text_parts:
        return
    author = event.author or "supply_chain_orchestrator"
    print(f"[{author}]:")
    print("".join(text_parts))
    print()


def _is_rate_limit_error(e: BaseException) -> bool:
    s = str(e).upper()
    return "429" in s or "RESOURCE_EXHAUSTED" in s


def _extract_retry_seconds(e: BaseException) -> int:
    """Parse 'Please retry in 53.18s' from error message; default 15 for exponential backoff base."""
    import re
    m = re.search(r"retry in (\d+(?:\.\d+)?)\s*s", str(e), re.I)
    if m:
        return min(120, max(10, int(float(m.group(1)) + 1)))
    return 15


def _backoff_seconds(attempt: int, api_suggested: int | None) -> float:
    """Exponential backoff: base * 2^attempt + 0–3s jitter, capped at 120s. Use api_suggested as base if provided."""
    import random
    base = api_suggested if api_suggested is not None else 15
    wait = min(120.0, base * (2 ** attempt)) + random.uniform(0, 3)
    return min(120.0, wait)


async def _retry_cycle(runner, session, prompt: str, max_retries: int = 3) -> None:
    """Run one cycle; on 429 wait with exponential backoff and retry up to max_retries times."""
    last_e = None
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0 and last_e:
                api_s = _extract_retry_seconds(last_e) if last_e else None
                wait_s = _backoff_seconds(attempt - 1, api_s)
                print(f"[429] Rate limit. Exponential backoff: waiting {wait_s:.0f}s (attempt {attempt + 1}/{max_retries + 1})...", file=sys.stderr)
                print("  Tip: RPM/TPM are per-minute; wait or use ORCHESTRATOR_USE_FLAT=1. See docs/RATE_LIMITS.md.", file=sys.stderr)
                await asyncio.sleep(wait_s)
            await run_one_cycle(runner, session, prompt)
            return
        except Exception as e:
            last_e = e
            if not _is_rate_limit_error(e):
                print(f"[error] {e}", file=sys.stderr)
                return
    if last_e:
        print(f"[error] Still rate limited after {max_retries + 1} attempts. Try --interval 120 or enable billing.", file=sys.stderr)
        print(f"  To use fewer API calls, run with: ORCHESTRATOR_USE_FLAT=1", file=sys.stderr)
        print(f"  {last_e}", file=sys.stderr)


async def run_one_cycle(runner, session, prompt: str) -> None:
    """Send one message to the agent and print all response events. Writes reasoning stream to ui/data/agent_reasoning_stream.json for the UI."""
    clear_reasoning_log()
    content = types.Content(role="user", parts=[types.Part(text=prompt)])
    async with aclosing(
        runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=content,
        )
    ) as agen:
        async for event in agen:
            _print_event(event)


async def main_async(interval_seconds: int, prompt: str, max_retries: int = 10) -> None:
    agent = _load_agent()
    print(f"[config] GEMINI_MODEL = {_RESOLVED_MODEL}", file=sys.stderr)
    mod = sys.modules.get("orchestrator_agent.agent")
    if mod is not None and getattr(mod, "_enabled", None) is not None:
        print(f"[config] ORCHESTRATOR_SUBAGENTS = {os.environ.get('ORCHESTRATOR_SUBAGENTS', 'all')} → {mod._enabled}", file=sys.stderr)
    # When no sub-agents we make 1 request only; use short prompt to minimize TPM
    if mod is not None and getattr(mod, "_enabled", None) == []:
        prompt = "Run diagnostic."
        print("[config] Using short diagnostic prompt (1 API request, no tools).", file=sys.stderr)
    app = App(name="orchestrator_agent", root_agent=agent)
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="orchestrator_agent",
        user_id="continuous_detection",
    )
    runner = Runner(
        app=app,
        artifact_service=InMemoryArtifactService(),
        session_service=session_service,
        memory_service=InMemoryMemoryService(),
        credential_service=InMemoryCredentialService(),
    )
    # Wait before first request so we're in a fresh rate-limit window (sub-agents = 2+ requests back-to-back)
    use_flat = os.environ.get("ORCHESTRATOR_USE_FLAT", "0").strip().lower() in ("1", "true", "yes")
    mod = sys.modules.get("orchestrator_agent.agent")
    no_subagents = mod is not None and getattr(mod, "_enabled", None) == []
    default_startup = 10 if (use_flat or no_subagents) else 15
    startup_delay = int(os.environ.get("STARTUP_DELAY_SECONDS", str(default_startup)))
    if not use_flat and not no_subagents and startup_delay < 15:
        startup_delay = 15
    if startup_delay > 0:
        print(f"Waiting {startup_delay}s before first run (avoids rate limit on startup)...", file=sys.stderr)
        await asyncio.sleep(startup_delay)
    cycle = 0
    try:
        while True:
            cycle += 1
            print(f"\n{'='*60}")
            print(f"Detection cycle {cycle}")
            print(f"{'='*60}\n")
            try:
                await _retry_cycle(runner, session, prompt, max_retries=max_retries)
            except Exception as e:
                if not _is_rate_limit_error(e):
                    print(f"[error] {e}", file=sys.stderr)
            if interval_seconds <= 0:
                break
            print(f"\nNext run in {interval_seconds}s (Ctrl+C to stop)...\n")
            await asyncio.sleep(interval_seconds)
    finally:
        await runner.close()


def main():
    parser = argparse.ArgumentParser(
        description="Run supply chain detection in a loop; prints briefing and takes actions each cycle."
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=120,
        help="Seconds between detection runs (default 120 for free tier). Use 0 to run once and exit.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=10,
        help="Max retries on 429 per cycle (default 10; Gemini free tier has strict RPM).",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default=DEFAULT_PROMPT,
        help="Prompt to send each cycle (default: full pipeline check).",
    )
    args = parser.parse_args()
    asyncio.run(main_async(interval_seconds=args.interval, prompt=args.prompt, max_retries=args.retries))


if __name__ == "__main__":
    main()
