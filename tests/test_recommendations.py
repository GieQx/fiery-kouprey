import pytest
from pydantic import ValidationError

from sdmx_alignment.models.recommendations import (
    StandardsRecommendationRequest,
    StandardsRecommendationResult,
)
from sdmx_alignment.models.reference import MethodologyPrinciple, SourceCitation
from sdmx_alignment.models.semantic import ProviderReadiness, SemanticElement
from sdmx_alignment.recommendations import (
    INSUFFICIENT_INFORMATION,
    recommend_standards,
    validate_recommendation,
)
from sdmx_alignment.semantic_matcher.base import ProviderError
from sdmx_alignment.semantic_matcher.no_llm_provider import NoLLMProvider


def _request() -> StandardsRecommendationRequest:
    return StandardsRecommendationRequest(
        finding_id="finding-1",
        local=SemanticElement(id="LOCAL_AREA", name="Area"),
        reference=SemanticElement(id="REF_AREA", name="Reference area"),
        allowed_local_ids=["LOCAL_AREA"],
        allowed_reference_ids=["REF_AREA"],
        allowed_codes=["A", "B"],
        principles=[
            MethodologyPrinciple(
                id="PRINCIPLE_1",
                text="Use internationally comparable classifications.",
                source_url="https://example.org/methodology",
            )
        ],
        citations=[
            SourceCitation(
                id="SOURCE_1",
                name="Reference standard",
                issuer="Example Agency",
                version="1.0",
                artefact_type="shared_sdmx_artefact_source",
                description="The selected structural reference.",
                source_url="https://example.org/reference",
            )
        ],
    )


def _result(**overrides) -> StandardsRecommendationResult:
    values = {
        "local_element_id": "LOCAL_AREA",
        "reference_element_id": "REF_AREA",
        "code_ids": ["A"],
        "recommendation": "Align the local area concept with the selected reference.",
        "reason": "The supplied labels describe the same statistical role.",
        "evidence": ["LOCAL_AREA is labelled Area; REF_AREA is labelled Reference area."],
        "citation_ids": ["SOURCE_1"],
        "principle_id": "PRINCIPLE_1",
        "confidence": 0.9,
        "provider": "fake",
        "model": "fake-model",
        "grounding_status": "grounded",
    }
    values.update(overrides)
    return StandardsRecommendationResult(**values)


class _Matcher:
    provider_name = "fake"

    def __init__(self, result=None, *, ready=True, error=None):
        self.result = result
        self.ready = ready
        self.error = error

    def is_ready(self):
        return ProviderReadiness(ready=self.ready, message="ready" if self.ready else "not ready")

    def recommend(self, request):
        if self.error:
            raise self.error
        return self.result


def test_valid_grounded_recommendation_is_returned_unchanged():
    expected = _result()

    result = recommend_standards(_request(), _Matcher(expected))

    assert result == expected
    assert validate_recommendation(_request(), result) is result


@pytest.mark.parametrize(
    ("overrides", "expected_status"),
    [
        ({"local_element_id": "INVENTED_LOCAL"}, "rejected"),
        ({"reference_element_id": "INVENTED_REFERENCE"}, "rejected"),
        ({"citation_ids": ["INVENTED_CITATION"]}, "rejected"),
        ({"code_ids": ["INVENTED_CODE"]}, "rejected"),
        ({"principle_id": "INVENTED_PRINCIPLE"}, "rejected"),
    ],
)
def test_ungrounded_identifiers_produce_exact_rejected_abstention(overrides, expected_status):
    result = recommend_standards(_request(), _Matcher(_result(**overrides)))

    assert result.recommendation == INSUFFICIENT_INFORMATION
    assert result.grounding_status == expected_status


def test_principle_claim_is_rejected_when_no_principle_was_supplied():
    request = _request().model_copy(update={"principles": []})

    result = recommend_standards(request, _Matcher(_result()))

    assert result.recommendation == INSUFFICIENT_INFORMATION
    assert result.grounding_status == "rejected"


@pytest.mark.parametrize("field", ["reason", "evidence"])
def test_missing_reason_or_evidence_is_malformed_and_rejected(field):
    payload = _result().model_dump()
    payload.pop(field)
    matcher = _Matcher(payload)

    result = recommend_standards(_request(), matcher)

    assert result.recommendation == INSUFFICIENT_INFORMATION
    assert result.grounding_status == "rejected"


@pytest.mark.parametrize(
    "malformed",
    [None, "not-json", {"recommendation": "partial"}],
)
def test_malformed_provider_output_produces_exact_rejected_abstention(malformed):
    result = recommend_standards(_request(), _Matcher(malformed))

    assert result.recommendation == INSUFFICIENT_INFORMATION
    assert result.grounding_status == "rejected"


def test_provider_failure_produces_exact_insufficient_abstention():
    result = recommend_standards(
        _request(),
        _Matcher(error=ProviderError("safe provider failure")),
    )

    assert result.recommendation == INSUFFICIENT_INFORMATION
    assert result.grounding_status == "insufficient"


def test_unready_matcher_does_not_call_provider_and_abstains():
    result = recommend_standards(_request(), _Matcher(ready=False, error=AssertionError("must not call")))

    assert result.recommendation == INSUFFICIENT_INFORMATION
    assert result.grounding_status == "insufficient"


def test_no_llm_provider_abstains_with_exact_sentence():
    result = recommend_standards(_request(), NoLLMProvider())

    assert result.recommendation == INSUFFICIENT_INFORMATION
    assert result.grounding_status == "insufficient"


def test_request_and_result_forbid_extra_fields_and_blank_text():
    with pytest.raises(ValidationError):
        StandardsRecommendationRequest(**_request().model_dump(), unexpected=True)
    with pytest.raises(ValidationError):
        _result(reason=" ")
    with pytest.raises(ValidationError):
        _result(evidence=[" "])
    with pytest.raises(ValidationError):
        _result(confidence=1.1)

