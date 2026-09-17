from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, computed_field


class SourceCitation(BaseModel):
    id: str
    name: str
    issuer: str
    version: str
    artefact_type: Literal["methodological_standard", "shared_sdmx_artefact_source"]
    description: str
    source_url: str
    published_at: date | None = None


class ReferenceStandard(BaseModel):
    agency_id: str
    artefact_id: str
    version: str
    name: str
    description: str
    domain: str
    issuer: str
    artefact_type: Literal["structural_reference"]
    provenance: str
    source_url: str | None = None
    retrieved_at: date
    fixture_classification: Literal["authoritative_reference", "synthetic_benchmark", "workshop_reference"]
    local_file: str
    related_sources: list[SourceCitation] = Field(default_factory=list)

    @computed_field
    @property
    def identity(self) -> str:
        return f"{self.agency_id}:{self.artefact_id}({self.version})"


class DiscoveryEvidence(BaseModel):
    signal: str
    count: int = Field(ge=0)
    examples: list[str] = Field(default_factory=list)


class DiscoveryCandidate(BaseModel):
    reference: ReferenceStandard
    evidence: list[DiscoveryEvidence]
    discovery_tier: Literal["strong", "plausible", "weak"]
    explanation: str
