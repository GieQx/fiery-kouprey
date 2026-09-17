from __future__ import annotations

import json

import httpx

from sdmx_alignment.models.semantic import ProviderReadiness, SemanticMatchRequest, SemanticMatchResult
from sdmx_alignment.semantic_matcher.base import BaseProvider, ProviderError
from sdmx_alignment.semantic_matcher.prompt import SYSTEM_PROMPT, user_prompt


def _match_response_schema(request: SemanticMatchRequest) -> dict:
    schema = SemanticMatchResult.model_json_schema()
    schema["properties"].pop("provider")
    schema["properties"].pop("model")
    schema["properties"]["suggested_reference_id"] = {
        "type": "string",
        "enum": [candidate.id for candidate in request.candidates],
    }
    schema["required"] = [
        field for field in schema["required"] if field not in {"provider", "model"}
    ]
    schema["required"].append("suggested_reference_id")
    return schema


class OllamaProvider(BaseProvider):
    provider_name = "ollama"

    def __init__(self, base_url: str, model: str, timeout: float = 30.0, client: httpx.Client | None = None):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.client = client or httpx.Client(base_url=self.base_url, timeout=timeout)

    def list_models(self) -> list[str]:
        try:
            response = self.client.get("/api/tags")
            response.raise_for_status()
            models = response.json().get("models")
            if not isinstance(models, list):
                raise ValueError("Ollama model list is missing")
            return [
                item["name"].strip()
                for item in models
                if isinstance(item, dict) and isinstance(item.get("name"), str) and item["name"].strip()
            ]
        except Exception as exc:
            raise ProviderError("Unable to discover Ollama models") from exc

    def is_ready(self) -> ProviderReadiness:
        if not self.base_url or not self.model:
            return ProviderReadiness(ready=False, message="Ollama endpoint and model are required")
        try:
            models = self.list_models()
        except ProviderError:
            return ProviderReadiness(ready=False, message="Ollama endpoint is unavailable")
        if self.model not in models:
            return ProviderReadiness(ready=False, message=f"Ollama model '{self.model}' is not installed")
        return ProviderReadiness(ready=True, message="Ollama configured")

    def match(self, request: SemanticMatchRequest) -> SemanticMatchResult:
        if not self.base_url or not self.model:
            raise ProviderError("Ollama endpoint and model are required")
        try:
            response = self.client.post(
                "/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "format": _match_response_schema(request),
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt(request)},
                    ],
                },
            )
            response.raise_for_status()
            payload = json.loads(response.json()["message"]["content"])
            payload.update(provider="ollama", model=self.model)
            return SemanticMatchResult.model_validate(payload)
        except Exception as exc:
            raise ProviderError("Ollama semantic matching failed") from exc

    def complete(self, question: str, context: dict) -> str:
        if not self.base_url or not self.model:
            raise ProviderError("Ollama endpoint and model are required")
        try:
            response = self.client.post(
                "/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Assess SDMX interoperability using only supplied evidence. Cite element IDs and mark uncertainty.",
                        },
                        {"role": "user", "content": question + "\n\nEvidence:\n" + json.dumps(context, ensure_ascii=True)},
                    ],
                },
            )
            response.raise_for_status()
            return str(response.json()["message"]["content"]).strip()
        except Exception as exc:
            raise ProviderError("Ollama assessment generation failed") from exc
