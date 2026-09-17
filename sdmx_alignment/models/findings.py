from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class CodeMapping(BaseModel):
    local_code: str
    local_label: str
    reference_code: str
    reference_label: str
    match_method: str = "exact_label"


class ElementEvidence(BaseModel):
    id: str
    label: str
    description: str = ""
    concept_ref: str | None = None
    codelist_ref: str | None = None
    representation: str | None = None
    source_path: str


class Finding(BaseModel):
    id: str
    element_type: str
    local: ElementEvidence | None = None
    reference: ElementEvidence | None = None
    match_method: str
    alignment_status: str
    finding_classification: str = "unresolved"
    relation: str = "not_applicable"
    confidence: float | None = None
    explanation: str
    deterministic_evidence: list[str] = Field(default_factory=list)
    code_mappings: list[CodeMapping] = Field(default_factory=list)
    is_ai_assisted: bool = False
    llm_provider: str | None = None
    llm_model: str | None = None
    review_status: str = "pending"
    recommended_action: str | None = None
    review_note: str = ""
    reviewed_at: datetime | None = None


class SummaryCounts(BaseModel):
    exact: int = 0
    semantic_suggestions: int = 0
    mapping_required: int = 0
    missing: int = 0
    unresolved: int = 0


class DSDIdentity(BaseModel):
    agency_id: str | None
    id: str
    version: str | None
    label: str
    file_name: str


class ComparisonResult(BaseModel):
    id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    local_dsd: DSDIdentity
    reference_dsd: DSDIdentity
    findings: list[Finding]
    summary: SummaryCounts
    ai_status: str = "disabled"
