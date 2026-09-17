from sdmx_alignment.config import LLMSettings
from sdmx_alignment.semantic_matcher.no_llm_provider import NoLLMProvider
from sdmx_alignment.semantic_matcher.ollama_provider import OllamaProvider
from sdmx_alignment.semantic_matcher.openai_provider import OpenAIProvider


def create_matcher(settings: LLMSettings):
    if settings.provider == "openai":
        if not settings.openai_api_key or not settings.openai_model:
            return NoLLMProvider("OpenAI key and model are required")
        return OpenAIProvider(
            settings.openai_api_key,
            settings.openai_model,
            timeout=settings.timeout_seconds,
        )
    if settings.provider == "ollama":
        if not settings.ollama_base_url or not settings.ollama_model:
            return NoLLMProvider("Ollama endpoint and model are required")
        return OllamaProvider(
            settings.ollama_base_url,
            settings.ollama_model,
            timeout=settings.timeout_seconds,
        )
    return NoLLMProvider()

