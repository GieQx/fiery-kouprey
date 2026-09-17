from __future__ import annotations

from sdmx_alignment.comparator.engine import refresh_summary
from sdmx_alignment.models.findings import ComparisonResult
from sdmx_alignment.semantic_matcher.base import SemanticMatcher, request_from_finding


def enrich_unresolved(result: ComparisonResult, matcher: SemanticMatcher) -> ComparisonResult:
    readiness = matcher.is_ready()
    if not readiness.ready:
        result.ai_status = "disabled"
        return refresh_summary(result)

    successes = 0
    failures = 0
    for finding in result.findings:
        if finding.alignment_status != "unresolved" or not finding.local or not finding.reference:
            continue
        try:
            request = request_from_finding(finding)
            suggestion = matcher.match(request)
            allowed_ids = {candidate.id for candidate in request.candidates}
            if suggestion.suggested_reference_id not in allowed_ids:
                raise ValueError("Provider selected an element outside the candidate set")
            finding.match_method = "ai_semantic"
            finding.relation = suggestion.relation
            finding.confidence = suggestion.confidence
            finding.explanation = suggestion.explanation
            finding.is_ai_assisted = True
            finding.llm_provider = suggestion.provider
            finding.llm_model = suggestion.model
            finding.review_status = "pending"
            if suggestion.relation in {"equivalent", "similar", "broader", "narrower"}:
                finding.alignment_status = "possible_equivalent"
                finding.finding_classification = "potential_semantic_correspondence"
            elif suggestion.relation == "incompatible":
                finding.finding_classification = "potential_semantic_conflict"
            else:
                finding.finding_classification = "insufficient_metadata"
            successes += 1
        except Exception:
            failures += 1
    result.ai_status = "partial_failure" if failures else ("enabled" if successes else "disabled")
    return refresh_summary(result)


def generate_assessment(question: str, context: dict, matcher: SemanticMatcher) -> str:
    readiness = matcher.is_ready()
    if not readiness.ready:
        raise RuntimeError(readiness.message)
    answer = matcher.complete(question, context).strip()
    if not answer:
        raise RuntimeError("The provider returned an empty assessment")
    return answer
