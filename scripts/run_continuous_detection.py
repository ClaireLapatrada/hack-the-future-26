#!/usr/bin/env python3
"""
Continuous supply chain detection — runs the orchestrator agent in a loop
without waiting for user input. Each cycle: run full pipeline, print briefing,
take actions, then sleep and repeat.

Run from project root:
  python scripts/run_continuous_detection.py
  python scripts/run_continuous_detection.py --interval 300   # 5 min

Uses the same orchestrator agent and tools as `adk run orchestrator_agent`;
env vars (GOOGLE_API_KEY, etc.) are loaded from orchestrator_agent/.env and
the project root.
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
    """Load orchestrator root_agent from orchestrator_agent/agent.py."""
    import importlib.util
    agent_path = PROJECT_ROOT / "orchestrator_agent" / "agent.py"
    spec = importlib.util.spec_from_file_location("orchestrator_agent.agent", agent_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["orchestrator_agent"] = type(sys)("orchestrator_agent")
    sys.modules["orchestrator_agent.agent"] = mod
    spec.loader.exec_module(mod)
    return getattr(mod, "root_agent")


def _print_event(event):
    """Print agent response text from an event."""
    if not event.content or not event.content.parts:
        return
    text_parts = [p.text for p in event.content.parts if p.text]
    if not text_parts:
        return
    author = event.author or "supply_chain_orchestrator"
    print(f"[{author}]:")
    print("".join(text_parts))
    print()


async def run_one_cycle(runner, session, prompt: str) -> None:
    """Send one message to the agent and print all response events."""
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


async def main_async(interval_seconds: int, prompt: str) -> None:
    agent = _load_agent()
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
    cycle = 0
    try:
        while True:
            cycle += 1
            print(f"\n{'='*60}")
            print(f"Detection cycle {cycle}")
            print(f"{'='*60}\n")
            try:
                await run_one_cycle(runner, session, prompt)
            except Exception as e:
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
        default=300,
        help="Seconds between detection runs (default 300). Use 0 to run once and exit.",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default=DEFAULT_PROMPT,
        help="Prompt to send each cycle (default: full pipeline check).",
    )
    args = parser.parse_args()
    asyncio.run(main_async(interval_seconds=args.interval, prompt=args.prompt))


if __name__ == "__main__":
    main()
