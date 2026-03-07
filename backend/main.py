"""
FastAPI application entry point.

Registers all routers and configures CORS so the Next.js frontend
(running on localhost:3000 by default) can call the API.

Start the server:
    uvicorn backend.main:app --reload --port 8000
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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

app = FastAPI(
    title="Supply Chain Resilience API",
    description="Backend API for the supply chain resilience agent.",
    version="1.0.0",
)

# Phase 10 (CORS hardening): read allowed origins from FRONTEND_ORIGIN env var.
# Falls back to localhost:3000 for local development.
_frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
_allowed_origins = [_frontend_origin]
# Also allow the legacy 3001 port in development only (not in production)
if os.getenv("ENVIRONMENT", "development") != "production":
    _allowed_origins += ["http://localhost:3001", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_stream.router)
app.include_router(approvals.router)
app.include_router(dashboard.router)
app.include_router(disruptions.router)
app.include_router(email.router)
app.include_router(events.router)
app.include_router(planning_documents.router)
app.include_router(profile.router)
app.include_router(rules.router)
app.include_router(scenarios.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/audit-log", response_class=JSONResponse)
def get_audit_log(n: int = 100) -> List[Dict[str, Any]]:
    """Return the last N entries from the append-only audit log (admin endpoint)."""
    from backend.tools.audit_log import get_audit_tail
    return get_audit_tail(n=min(n, 1000))
