"""
FastAPI application entry point.

Registers all routers and configures CORS so the Next.js frontend
(running on localhost:3000 by default) can call the API.

Start the server:
    uvicorn backend.main:app --reload --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

app = FastAPI(
    title="Supply Chain Resilience API",
    description="Backend API for AutomotiveParts GmbH supply chain resilience agent.",
    version="1.0.0",
)

# Allow the Next.js dev server and any localhost port to reach the API.
# Tighten this list before production deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_stream.router)
app.include_router(approvals.router)
app.include_router(dashboard.router)
app.include_router(disruptions.router)
app.include_router(events.router)
app.include_router(planning_documents.router)
app.include_router(rules.router)
app.include_router(scenarios.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
