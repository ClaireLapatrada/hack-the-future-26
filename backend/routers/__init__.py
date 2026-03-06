# FastAPI routers — one module per resource group.
from backend.routers import (
    agent_stream,
    approvals,
    dashboard,
    disruptions,
    events,
    planning_documents,
    rules,
    scenarios,
)

__all__ = [
    "agent_stream",
    "approvals",
    "dashboard",
    "disruptions",
    "events",
    "planning_documents",
    "rules",
    "scenarios",
]
