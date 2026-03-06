"""
Per-minute rate limiter — avoids 429 by keeping request count under RPM in a sliding 60s window.

Limits are per minute (RPM), not per day. Bursts trigger 429 even when daily usage is low.
Set RATE_LIMIT_RPM in env (e.g. 8) to stay under your tier's limit (e.g. 15 RPM).
"""

import os
import threading
import time
from collections import deque
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(PROJECT_ROOT / "orchestrator_agent" / ".env")
except ImportError:
    pass

try:
    _rpm = int(os.getenv("RATE_LIMIT_RPM", "0"))
    RATE_LIMIT_RPM = max(0, min(60, _rpm))  # 0 = disabled
except (TypeError, ValueError):
    RATE_LIMIT_RPM = 0

_WINDOW_SECONDS = 60
_lock = threading.Lock()
_timestamps: deque[float] = deque()


def record_request() -> None:
    """Record one request at current time (call before or after the API call that counts toward quota)."""
    if RATE_LIMIT_RPM <= 0:
        return
    with _lock:
        _timestamps.append(time.monotonic())


def wait_if_needed() -> None:
    """
    If we've had >= RATE_LIMIT_RPM requests in the last 60s, block until the oldest drops out.
    Call before each action that triggers an API call (tool run, sub-agent run).
    """
    if RATE_LIMIT_RPM <= 0:
        return
    while True:
        with _lock:
            now = time.monotonic()
            cutoff = now - _WINDOW_SECONDS
            while _timestamps and _timestamps[0] < cutoff:
                _timestamps.popleft()
            if len(_timestamps) < RATE_LIMIT_RPM:
                return
            wait_s = _timestamps[0] + _WINDOW_SECONDS - now
            wait_s = max(0.5, min(60.0, wait_s))
        time.sleep(wait_s)
