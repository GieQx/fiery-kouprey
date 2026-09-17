from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SemanticElement(BaseModel):
    id: str
    name: str | None = None
    description: str | None = None
    annotations: list[str] = Field(default_factory=list)


class SemanticMatchRequest(BaseModel):
    local: SemanticElement
    candidates: list[SemanticElement]


class SemanticMatchResult(BaseModel):
    suggested_reference_id: str | None = None
    relation: Literal["equivalent", "similar", "broader", "narrower", "uncertain", "incompatible"]
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str = Field(min_length=1, max_length=600)
    provider: str
    model: str


class ProviderReadiness(BaseModel):
    ready: bool
    message: str

