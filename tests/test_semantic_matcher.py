import json
from pathlib import Path

import httpx
import pytest

from sdmx_alignment.comparator.engine import compare_structures
from sdmx_alignment.models.semantic import SemanticMatchResult
from sdmx_alignment.parser.sdmx_structure import parse_structure
from sdmx_alignment.semantic_matcher.base import ProviderReadiness
from sdmx_alignment.semantic_matcher.base import ProviderError
from sdmx_alignment.semantic_matcher.ollama_provider import OllamaProvider
from sdmx_alignment.semantic_matcher.openai_provider import OpenAIProvider
from sdmx_alignment.semantic_matcher.service import enrich_unresolved
from sdmx_alignment.semantic_matcher.service import generate_assessment


FIXTURES = Path(__file__).parent / "fixtures"


def _comparison():
    local = parse_structure("local.xml", (FIXTURES / "local-demo.xml").read_bytes())
    reference = parse_structure("reference.xml", (FIXTURES / "reference-demo.xml").read_bytes())
    return compare_structures(local, reference)


class FakeMatcher:
    provider_name = "fake"

    def is_ready(self):
        return ProviderReadiness(ready=True, message="ready")

    def match(self, request):
        return SemanticMatchResult(
            suggested_reference_id=request.candidates[0].id,
            relation="equivalent",
            confidence=0.91,
            explanation="The definitions describe the same statistical role.",
            provider="openai",
            model="test-model",
        )

    def complete(self, question, context):
        assert "interoperate" in question
        assert "local" in context
        return "Evidence-based interoperability assessment"


def test_semantic_service_enriches_only_unresolved_pairs():
    result = enrich_unresolved(_comparison(), FakeMatcher())

    area = next(item for item in result.findings if item.local and item.local.id == "AREA")
    sex = next(item for item in result.findings if item.local and item.local.id == "SEX")
    assert area.alignment_status == "possible_equivalent"
    assert area.match_method == "ai_semantic"
    assert area.is_ai_assisted is True
    assert area.review_status == "pending"
    assert area.confidence == 0.91
    assert sex.is_ai_assisted is False
    assert result.ai_status == "enabled"
    assert result.summary.semantic_suggestions == 2


def test_assessment_uses_provider_neutral_completion_contract():
    answer = generate_assessment("How can these DSDs interoperate?", {"local": {}, "reference": {}}, FakeMatcher())

    assert answer == "Evidence-based interoperability assessment"


class _FakeMessage:
    content = json.dumps({
        "suggested_reference_id": "REF_AREA",
        "relation": "equivalent",
        "confidence": 0.88,
        "explanation": "Both identify the reference geography.",
    })


class _FakeChoice:
    message = _FakeMessage()


class _FakeCompletions:
    def create(self, **kwargs):
        assert kwargs["model"] == "configured-openai-model"
        return type("Response", (), {"choices": [_FakeChoice()]})()


class _FakeOpenAIClient:
    chat = type("Chat", (), {"completions": _FakeCompletions()})()


def test_openai_provider_returns_provider_neutral_result():
    provider = OpenAIProvider("secret", "configured-openai-model", client=_FakeOpenAIClient())
    finding = next(item for item in _comparison().findings if item.local and item.local.id == "AREA")
    request = provider.request_from_finding(finding)

    result = provider.match(request)

    assert result.provider == "openai"
    assert result.model == "configured-openai-model"
    assert result.suggested_reference_id == "REF_AREA"


def test_ollama_provider_uses_configured_endpoint_and_model():
    def handler(request: httpx.Request):
        assert request.url.path == "/api/chat"
        payload = json.loads(request.content)
        assert payload["model"] == "local-model"
        assert payload["format"]["type"] == "object"
        assert "suggested_reference_id" in payload["format"]["properties"]
        assert payload["format"]["properties"]["suggested_reference_id"]["type"] == "string"
        assert payload["format"]["properties"]["suggested_reference_id"]["enum"] == ["REF_AREA"]
        assert set(payload["format"]["required"]) == {
            "suggested_reference_id",
            "relation",
            "confidence",
            "explanation",
        }
        return httpx.Response(200, json={"message": {"content": json.dumps({
            "suggested_reference_id": "REF_AREA",
            "relation": "similar",
            "confidence": 0.76,
            "explanation": "Both are geographic concepts.",
        })}})

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://ollama.test")
    provider = OllamaProvider("http://ollama.test", "local-model", client=client)
    finding = next(item for item in _comparison().findings if item.local and item.local.id == "AREA")

    result = provider.match(provider.request_from_finding(finding))

    assert result.provider == "ollama"
    assert result.model == "local-model"
    assert result.relation == "similar"


def test_ollama_provider_lists_installed_models_in_response_order():
    def handler(request: httpx.Request):
        assert request.url.path == "/api/tags"
        return httpx.Response(200, json={"models": [
            {"name": "qwen2.5:0.5b"},
            {"name": "llama3.2:3b"},
        ]})

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://ollama.test")
    provider = OllamaProvider("http://ollama.test", "", client=client)

    assert provider.list_models() == ["qwen2.5:0.5b", "llama3.2:3b"]


def test_ollama_provider_rejects_malformed_model_response():
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"models": "invalid"})),
        base_url="http://ollama.test",
    )
    provider = OllamaProvider("http://ollama.test", "", client=client)

    with pytest.raises(ProviderError, match="Unable to discover Ollama models"):
        provider.list_models()


def test_ollama_provider_wraps_model_discovery_connection_errors():
    def handler(request: httpx.Request):
        raise httpx.ConnectError("offline", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://ollama.test")
    provider = OllamaProvider("http://ollama.test", "", client=client)

    with pytest.raises(ProviderError, match="Unable to discover Ollama models"):
        provider.list_models()


def test_ollama_provider_is_not_ready_when_selected_model_is_missing():
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"models": [{"name": "another-model"}]})
        ),
        base_url="http://ollama.test",
    )
    provider = OllamaProvider("http://ollama.test", "removed-model", client=client)

    readiness = provider.is_ready()

    assert readiness.ready is False
    assert "removed-model" in readiness.message
