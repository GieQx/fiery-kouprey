from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StrictBool,
    StringConstraints,
    TypeAdapter,
    computed_field,
    model_validator,
)


_HTTP_URL_ADAPTER = TypeAdapter(HttpUrl)


def _validate_http_url(value: str) -> str:
    _HTTP_URL_ADAPTER.validate_python(value)
    return value


NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
HttpUrlString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
    AfterValidator(_validate_http_url),
]


class TrustedSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: NonEmptyString
    name: NonEmptyString
    source_type: Literal["registry", "institutional_repository", "curated_repository"]
    base_url: HttpUrlString
    trust_level: Literal["authoritative", "curated"]
    is_default: StrictBool = False


class MethodologyPrinciple(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: NonEmptyString
    text: NonEmptyString
    source_url: HttpUrlString


class MethodologyStandard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: NonEmptyString
    name: NonEmptyString
    issuer: NonEmptyString
    version: NonEmptyString
    description: NonEmptyString
    source_url: HttpUrlString
    domains: list[NonEmptyString] = Field(min_length=1)
    published_at: date | None = None
    principles: list[MethodologyPrinciple] = Field(default_factory=list, min_length=1, max_length=5)


class SourceCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: NonEmptyString
    name: NonEmptyString
    issuer: NonEmptyString
    version: NonEmptyString
    artefact_type: Literal["methodological_standard", "shared_sdmx_artefact_source"]
    description: NonEmptyString
    source_url: HttpUrlString
    published_at: date | None = None


class ReferenceStandard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agency_id: NonEmptyString
    artefact_id: NonEmptyString
    version: NonEmptyString
    name: NonEmptyString
    description: NonEmptyString
    domain: NonEmptyString
    issuer: NonEmptyString
    artefact_type: Literal["structural_reference"]
    provenance: NonEmptyString
    source_url: HttpUrlString | None = None
    retrieved_at: date
    fixture_classification: Literal["authoritative_reference", "synthetic_benchmark", "workshop_reference"]
    local_file: NonEmptyString
    source_id: NonEmptyString = "CURATED_LOCAL"
    retrieval_mode: Literal["live", "cache", "curated"] = "curated"
    trust_level: Literal["authoritative", "curated"] = "curated"
    related_sources: list[SourceCitation] = Field(default_factory=list)

    @model_validator(mode="after")
    def prevent_provenance_laundering(self) -> ReferenceStandard:
        if self.fixture_classification in {"synthetic_benchmark", "workshop_reference"}:
            if self.retrieval_mode == "live":
                raise ValueError(
                    f"{self.fixture_classification} cannot claim live retrieval"
                )
            if self.trust_level == "authoritative":
                raise ValueError(
                    f"{self.fixture_classification} cannot claim authoritative trust"
                )
        if self.source_id.casefold() == "curated_local" and self.trust_level == "authoritative":
            raise ValueError("CURATED_LOCAL cannot claim authoritative trust")
        return self

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
