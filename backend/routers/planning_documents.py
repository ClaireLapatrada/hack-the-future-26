"""
GET /api/planning-documents        — list all planning documents, newest first
GET /api/planning-documents/{id}   — get a single document by ID

Mirrors ui/app/api/planning-documents/route.ts and [id]/route.ts.
"""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from backend.data import DataStore, get_data_store

router = APIRouter()


@router.get("/api/planning-documents", response_model=List[Dict[str, Any]])
def list_planning_documents(
    store: DataStore = Depends(get_data_store),
) -> List[Dict[str, Any]]:
    """Return all planning documents sorted by createdAt descending."""
    docs = store.load_planning_documents()
    raw = [d.model_dump() for d in docs]
    raw.sort(
        key=lambda d: d.get("createdAt") or "",
        reverse=True,
    )
    return raw


@router.get("/api/planning-documents/{document_id}", response_model=Dict[str, Any])
def get_planning_document(
    document_id: str,
    store: DataStore = Depends(get_data_store),
) -> Dict[str, Any]:
    """Return a single planning document by ID."""
    docs = store.load_planning_documents()
    for doc in docs:
        if doc.id == document_id:
            return doc.model_dump()
    raise HTTPException(status_code=404, detail="Planning document not found")
