#!/usr/bin/env python3
"""
Verify that Google Custom Search and NASA EONET env vars are loaded and report
why 403 might occur. Run from project root: python scripts/check_perception_env.py
Does not print secret values; only reports whether keys are set and length.
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(PROJECT_ROOT / "perception_agent" / ".env")
    load_dotenv(PROJECT_ROOT / "orchestrator_agent" / ".env")
except ImportError:
    pass

def mask(s: str) -> str:
    if not s or len(s) < 8:
        return "(not set or too short)"
    return f"{s[:4]}...{s[-4:]} ({len(s)} chars)"

print("Perception env check (keys masked)\n")
print("Google Custom Search:")
api_key = os.getenv("GOOGLE_SEARCH_API_KEY") or os.getenv("GOOGLE_API_KEY")
cx = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
print(f"  GOOGLE_SEARCH_API_KEY or GOOGLE_API_KEY: {mask(api_key) if api_key else '(missing)'}")
print(f"  GOOGLE_SEARCH_ENGINE_ID (cx):            {mask(cx) if cx else '(missing)'}")
if api_key and cx:
    print("  → Keys are set. If you still get 403:")
    print("    1. Enable 'Custom Search API' in Google Cloud Console (APIs & Services).")
    print("    2. If the API key has 'HTTP referrer' restriction, it won't work from Python.")
    print("       Use restriction 'None' or 'IP addresses' for CLI/server.")
else:
    print("  → Set both in .env or orchestrator_agent/.env (or perception_agent/.env).")

print("\nNASA EONET (optional):")
nasa = os.getenv("NASA_API_KEY")
print(f"  NASA_API_KEY: {mask(nasa) if nasa else '(not set — optional)'}")

print("\nGemini (for supplier health):")
gemini = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
print(f"  GEMINI_API_KEY or GOOGLE_API_KEY: {mask(gemini) if gemini else '(missing)'}")
