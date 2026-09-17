from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from sdmx_alignment.models.reference import MethodologyPrinciple, SourceCitation
from sdmx_alignment.models.semantic import SemanticElement


BoundedText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=1200),
]
Identifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=240),
]


class StandardsRecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: Identifier
    local: SemanticElement | None = None
    reference: SemanticElement | None = None
    allowed_local_ids: list[Identifier] = Field(default_factory=list)
    allowed_reference_ids: list[Identifier] = Field(default_factory=list)
    allowed_codes: list[Identifier] = Field(default_factory=list)
    principles: list[MethodologyPrinciple] = Field(default_factory=list)
    citations: list[SourceCitation] = Field(default_factory=list)


class StandardsRecommendationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local_element_id: Identifier | None = None
    reference_element_id: Identifier | None = None
    code_ids: list[Identifier] = Field(default_factory=list)
    recommendation: BoundedText
    reason: BoundedText
    evidence: list[BoundedText] = Field(min_length=1, max_length=20)
    citation_ids: list[Identifier] = Field(default_factory=list)
    principle_id: Identifier | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    provider: Identifier
    model: Identifier
    grounding_status: Literal["grounded", "insufficient", "rejected"]
