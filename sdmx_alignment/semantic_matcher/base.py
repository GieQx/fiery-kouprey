from __future__ import annotations

from typing import Protocol

from sdmx_alignment.models.findings import Finding
from sdmx_alignment.models.recommendations import (
    StandardsRecommendationRequest,
    StandardsRecommendationResult,
)
from sdmx_alignment.models.semantic import (
    ProviderReadiness,
    SemanticElement,
    SemanticMatchRequest,
    SemanticMatchResult,
)


class SemanticMatcher(Protocol):
    provider_name: str

    def is_ready(self) -> ProviderReadiness: ...

    def match(self, request: SemanticMatchRequest) -> SemanticMatchResult: ...

    def recommend(
        self, request: StandardsRecommendationRequest
    ) -> StandardsRecommendationResult: ...

    def complete(self, question: str, context: dict) -> str: ...


class ProviderError(RuntimeError):
    """Safe provider error that may be shown without leaking credentials."""


def request_from_finding(finding: Finding) -> SemanticMatchRequest:
    if finding.local is None or finding.reference is None:
        raise ProviderError("Semantic matching requires both local and reference evidence")
    return SemanticMatchRequest(
        local=SemanticElement(
            id=finding.local.id,
            name=finding.local.label,
            description=finding.local.description,
        ),
        candidates=[
            SemanticElement(
                id=finding.reference.id,
                name=finding.reference.label,
                description=finding.reference.description,
            )
        ],
    )


class BaseProvider:
    provider_name = "base"

    @staticmethod
    def request_from_finding(finding: Finding) -> SemanticMatchRequest:
        return request_from_finding(finding)
