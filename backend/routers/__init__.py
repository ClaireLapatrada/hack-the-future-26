# FastAPI routers — one module per resource group.
from backend.routers import (
    agent_stream,
    approvals,
    dashboard,
    disruptions,
    email,
    events,
    planning_documents,
    profile,
    rules,
    scenarios,
)

__all__ = [
    "agent_stream",
    "approvals",
    "dashboard",
    "disruptions",
    "email",
    "events",
    "planning_documents",
    "profile",
    "rules",
    "scenarios",
]
