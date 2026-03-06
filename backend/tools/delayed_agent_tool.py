"""
DelayedAgentTool — Wraps AgentTool and sleeps before each sub-agent run to avoid 429.

The runner invokes run_async when the model calls a sub-agent. We sleep first, then delegate.
Set SUBAGENT_BREATHER_SECONDS in env (default 30). Uses RPM limiter if RATE_LIMIT_RPM set.
"""

import asyncio
import os
import sys

from google.adk.tools.agent_tool import AgentTool

try:
    from tools.rate_limiter import wait_if_needed, record_request
except ImportError:
    def wait_if_needed() -> None: ...
    def record_request() -> None: ...


def _delay_seconds() -> int:
    v = int(os.environ.get("SUBAGENT_BREATHER_SECONDS", "10"))
    return max(0, min(120, v))


class DelayedAgentTool(AgentTool):
    """AgentTool that waits SUBAGENT_BREATHER_SECONDS before running the sub-agent."""

    def __init__(self, agent, delay_seconds: int | None = None, **kwargs):
        super().__init__(agent=agent, **kwargs)
        self._delay = delay_seconds if delay_seconds is not None else _delay_seconds()

    async def run_async(self, *, args, tool_context):
        # Per-minute cap (RPM); blocks if we've hit limit in last 60s
        wait_if_needed()
        record_request()
        if self._delay > 0:
            print(f"[rate limit] Waiting {self._delay}s before sub-agent '{self.agent.name}'...", file=sys.stderr)
            await asyncio.sleep(self._delay)
        return await super().run_async(args=args, tool_context=tool_context)
