from __future__ import annotations

from pydantic import ValidationError

from sdmx_alignment.models.recommendations import (
    StandardsRecommendationRequest,
    StandardsRecommendationResult,
)
from sdmx_alignment.semantic_matcher.base import ProviderError, SemanticMatcher


INSUFFICIENT_INFORMATION = "Insufficient information for a reliable recommendation."


def _abstention(
    request: StandardsRecommendationRequest,
    matcher: SemanticMatcher,
    status: str,
) -> StandardsRecommendationResult:
    return StandardsRecommendationResult(
        local_element_id=(
            request.local.id
            if request.local is not None and request.local.id in request.allowed_local_ids
            else None
        ),
        reference_element_id=(
            request.reference.id
            if request.reference is not None
            and request.reference.id in request.allowed_reference_ids
            else None
        ),
        code_ids=[],
        recommendation=INSUFFICIENT_INFORMATION,
        reason=INSUFFICIENT_INFORMATION,
        evidence=[INSUFFICIENT_INFORMATION],
        citation_ids=[],
        principle_id=None,
        confidence=0.0,
        provider=getattr(matcher, "provider_name", "unknown") or "unknown",
        model="unavailable",
        grounding_status=status,
    )


def validate_recommendation(
    request: StandardsRecommendationRequest,
    result: StandardsRecommendationResult,
) -> StandardsRecommendationResult:
    if result.grounding_status != "grounded":
        raise ValueError("Provider result is not grounded")
    if result.local_element_id not in request.allowed_local_ids:
        raise ValueError("Local element ID is not grounded")
    if result.reference_element_id not in request.allowed_reference_ids:
        raise ValueError("Reference element ID is not grounded")
    if not set(result.code_ids).issubset(request.allowed_codes):
        raise ValueError("Code ID is not grounded")
    if not set(result.citation_ids).issubset(citation.id for citation in request.citations):
        raise ValueError("Citation ID is not grounded")
    allowed_principles = {principle.id for principle in request.principles}
    if result.principle_id is not None and result.principle_id not in allowed_principles:
        raise ValueError("Methodology principle ID is not grounded")
    return result


def recommend_standards(
    request: StandardsRecommendationRequest,
    matcher: SemanticMatcher,
) -> StandardsRecommendationResult:
    try:
        if not matcher.is_ready().ready:
            return _abstention(request, matcher, "insufficient")
        raw_result = matcher.recommend(request)
    except ProviderError:
        return _abstention(request, matcher, "insufficient")

    try:
        result = StandardsRecommendationResult.model_validate(raw_result)
        return validate_recommendation(request, result)
    except (ValidationError, TypeError, ValueError):
        return _abstention(request, matcher, "rejected")
