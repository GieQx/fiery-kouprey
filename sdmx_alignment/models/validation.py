from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from sdmx_alignment.models.findings import SummaryCounts


class TechnicalCheck(BaseModel):
    id: str
    name: str
    status: Literal["PASS", "FAIL"]
    message: str


class TechnicalValidationResult(BaseModel):
    status: Literal["PASS", "FAIL"]
    checks: list[TechnicalCheck] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    disclaimer: str


class ReferenceAlignmentAssessment(BaseModel):
    status: Literal["ALIGNED", "PARTIALLY_ALIGNED", "ISSUES_REMAIN"]
    summary: SummaryCounts
    outstanding_code_mappings: int
    unresolved_semantic_issues: int
    local_extensions_retained: int
    disclaimer: str


class BeforeAfterReport(BaseModel):
    before: SummaryCounts
    after: SummaryCounts
    exact_alignment_delta: int
    unresolved_delta: int
    applied_changes: int
    human_approved_changes: int
    deterministic_findings: int
    ai_assisted_findings: int

