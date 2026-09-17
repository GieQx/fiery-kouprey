from sdmx_alignment.config import LLMSettings, choose_ollama_model
from sdmx_alignment.semantic_matcher.factory import create_matcher
from sdmx_alignment.semantic_matcher.no_llm_provider import NoLLMProvider
from sdmx_alignment.semantic_matcher.ollama_provider import OllamaProvider


def test_missing_openai_configuration_falls_back_to_no_llm():
    matcher = create_matcher(LLMSettings(provider="openai", openai_api_key="", openai_model=""))

    assert isinstance(matcher, NoLLMProvider)
    assert "key and model" in matcher.is_ready().message


def test_complete_ollama_configuration_creates_ollama_provider():
    matcher = create_matcher(
        LLMSettings(provider="ollama", ollama_base_url="http://localhost:11434", ollama_model="qwen-test")
    )

    assert isinstance(matcher, OllamaProvider)
    assert matcher.model == "qwen-test"


def test_configured_installed_ollama_model_is_selected():
    models = ["qwen2.5:0.5b", "llama3.2:3b"]

    assert choose_ollama_model(models, "llama3.2:3b") == "llama3.2:3b"


def test_first_discovered_ollama_model_is_selected_by_default():
    models = ["qwen2.5:0.5b", "llama3.2:3b"]

    assert choose_ollama_model(models, "missing-model") == "qwen2.5:0.5b"


def test_no_ollama_model_is_selected_when_discovery_is_empty():
    assert choose_ollama_model([], "configured-model") == ""
