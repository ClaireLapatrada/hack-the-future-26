#!/usr/bin/env python3
"""
List Gemini models available in your project (Google AI API).

Uses GOOGLE_API_KEY from the environment, or loads from orchestrator_agent/.env
if present. Run from the project root:

    python scripts/list_gemini_models.py

Use this to pick a model for GEMINI_MODEL if you get 404 (model not found)
or 400 (tool use unsupported).
"""

import os
import sys
from pathlib import Path

# Project root: parent of scripts/
ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

# Load .env from orchestrator_agent if present
env_file = ROOT / "orchestrator_agent" / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

def main():
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Set GOOGLE_API_KEY or add it to orchestrator_agent/.env", file=sys.stderr)
        sys.exit(1)

    try:
        from google import genai
    except ImportError:
        print("Install google-genai: pip install google-genai", file=sys.stderr)
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    print("Gemini models available in your project (generateContent):\n")
    for m in client.models.list():
        name = getattr(m, "name", None) or getattr(m, "display_name", str(m))
        if not name or "gemini" not in name.lower():
            continue
        if "embedding" in name.lower() or "embed" in name.lower():
            continue
        # Strip models/ prefix for readability
        if name.startswith("models/"):
            name = name[7:]
        print(f"  {name}")
    print("\nSet one with: export GEMINI_MODEL=<model_id>")

if __name__ == "__main__":
    main()
