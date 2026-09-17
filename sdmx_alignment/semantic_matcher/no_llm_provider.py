from sdmx_alignment.models.semantic import ProviderReadiness, SemanticMatchRequest, SemanticMatchResult
from sdmx_alignment.semantic_matcher.base import BaseProvider, ProviderError


class NoLLMProvider(BaseProvider):
    provider_name = "none"

    def __init__(self, message: str = "No LLM configured"):
        self.message = message

    def is_ready(self) -> ProviderReadiness:
        return ProviderReadiness(ready=False, message=self.message)

    def match(self, request: SemanticMatchRequest) -> SemanticMatchResult:
        raise ProviderError(self.message)

    def complete(self, question: str, context: dict) -> str:
        raise ProviderError(self.message)
