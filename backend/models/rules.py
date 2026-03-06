"""Pydantic models for the rules/config UI (config/rules.json)."""
from __future__ import annotations

from typing import Annotated, Any, Dict, List, Literal, Union

from pydantic import BaseModel, Field


class SliderRule(BaseModel):
    type: Literal["slider"]
    key: str
    name: str
    description: str
    min: float
    max: float
    unit: str = ""


class InputRule(BaseModel):
    type: Literal["input"]
    key: str
    name: str
    description: str


class ToggleRule(BaseModel):
    type: Literal["toggle"]
    key: str
    name: str
    description: str


RuleDef = Annotated[Union[SliderRule, InputRule, ToggleRule], Field(discriminator="type")]


class RuleSection(BaseModel):
    group: str
    icon: str
    rules: List[RuleDef]


class RulesConfig(BaseModel):
    sections: List[RuleSection]
    initialValues: Dict[str, Any]
