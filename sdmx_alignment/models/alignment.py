from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, computed_field, field_validator

from sdmx_alignment.models.findings import DSDIdentity


class AlignmentDecision(BaseModel):
    finding_id: str
    local_element_id: str | None = None
    reference_element_id: str | None = None
    recommended_action: Literal["REUSE", "MAP", "KEEP_LOCAL_EXTENSION", "ADD_MISSING_ELEMENT"]
    relation: str
    confidence: float | None = None
    evidence: list[str]
    reviewer_status: str
    reviewer_note: str = ""
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AlignmentPlan(BaseModel):
    local_dsd: DSDIdentity
    reference_dsd: DSDIdentity
    decisions: list[AlignmentDecision] = Field(default_factory=list)
    unresolved_finding_ids: list[str] = Field(default_factory=list)
    status: Literal["draft", "final"] = "draft"
    reviewer: str | None = None
    finalized_at: datetime | None = None


SCORE_KEYS = ("reuse", "code_mapping", "gaps", "limitations", "evidence")


class AnswerEvaluation(BaseModel):
    fixed_question: str
    provider: str
    model: str
    capture_method: Literal["in_app", "pasted"]
    context_hash: str
    baseline_answer: str
    improved_answer: str
    baseline_scores: dict[str, int]
    improved_scores: dict[str, int]
    critical_errors: list[str] = Field(default_factory=list)
    evaluator_note: str = ""

    @field_validator("baseline_scores", "improved_scores")
    @classmethod
    def validate_scores(cls, value: dict[str, int]):
        if set(value) != set(SCORE_KEYS):
            raise ValueError(f"Scores must contain exactly: {', '.join(SCORE_KEYS)}")
        if any(score not in {0, 1, 2} for score in value.values()):
            raise ValueError("Each answer score must be 0, 1, or 2")
        return value

    @computed_field
    @property
    def baseline_total(self) -> int:
        return sum(self.baseline_scores.values())

    @computed_field
    @property
    def improved_total(self) -> int:
        return sum(self.improved_scores.values())

    @computed_field
    @property
    def measured_delta(self) -> int:
        return self.improved_total - self.baseline_total
