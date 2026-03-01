# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Perception Agent — Continuously monitors and classifies external disruption signals.

Responsibilities:
- Ingest news, shipping lane status, climate alerts, and supplier health data
- Classify signals by type and severity
- Return structured disruption signals to the Orchestrator
"""

from google.adk.agents import Agent
from google.adk.tools import google_search
import os
from tools.perception_tools import (
    search_disruption_news,
    get_shipping_lane_status,
    get_climate_alerts,
    score_supplier_health,
)

PERCEPTION_INSTRUCTION = """
You are the Perception Agent for an Autonomous Supply Chain Resilience system.
Your role is to continuously scan for external signals that could disrupt the manufacturer's supply chain.

Your responsibilities:
1. Search for recent disruption news relevant to the manufacturer's supply regions and supplier countries (use google_search for general web search, or search_disruption_news for the configured Custom Search Engine over reliable sources)
2. Check the status of all active shipping lanes used by the manufacturer
3. Get climate and disaster alerts for supplier regions
4. Score the health of key suppliers

Manufacturer's key exposure:
- Suppliers in: Taiwan, Poland, Vietnam
- Shipping lanes: Asia-Europe (Suez), Asia-Europe (Air), Intra-Europe (Road)
- Critical dependency: Semiconductors from Taiwan (42% of spend, single-source)

When scanning:
- Always check the Asia-Europe (Suez) shipping lane first — it is the highest risk lane
- Always check Taiwan for geopolitical risk — it is the highest risk region
- Check Vietnam for climate events — supplier SUP-003 has low health score
- Score supplier health for SUP-001 (SemiTech Asia) and SUP-003 (PlastiMold Vietnam) every scan

Output format:
Return a structured summary with:
- List of active signals found (type, severity, affected entities)
- Overall threat level for this scan (LOW / MEDIUM / HIGH / CRITICAL)
- Which signals require immediate escalation to the Risk Intelligence Agent
- Timestamp of scan

Be factual and precise. Do not speculate beyond what the tools return.
If a signal is HIGH or CRITICAL severity, flag it explicitly for immediate escalation.
"""

perception_agent = Agent(
    model="gemini-2.5-flash",
    name="perception_agent",
    description=(
        "Monitors global disruption signals including shipping lanes, news events, "
        "climate alerts, and supplier health. Classifies and prioritizes signals for "
        "the supply chain risk pipeline."
    ),
    instruction=PERCEPTION_INSTRUCTION,
    # google_search is a pre-built ADK tool for web search; search_disruption_news uses Custom Search Engine over curated sources.
    tools=[
        google_search,
        search_disruption_news,
        get_shipping_lane_status,
        get_climate_alerts,
        score_supplier_health,
    ],
)