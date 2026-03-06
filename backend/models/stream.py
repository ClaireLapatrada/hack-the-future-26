"""Pydantic models for the agent reasoning stream."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel


class StreamEntryType(str, Enum):
    OBSERVE = "OBSERVE"
    ACTION = "ACTION"
    RESULT = "RESULT"
    REASON = "REASON"
    REASONING = "REASONING"
    PLANNING = "PLANNING"
    MEMORY = "MEMORY"
    TOOL = "TOOL"


class StreamEntry(BaseModel):
    type: StreamEntryType
    time: str
    content: str
    confidence: Optional[str] = None
    category: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    detail: Optional[str] = None
