from __future__ import annotations

import json

from sdmx_alignment.models.recommendations import (
    StandardsRecommendationRequest,
    StandardsRecommendationResult,
)
from sdmx_alignment.models.semantic import ProviderReadiness, SemanticMatchRequest, SemanticMatchResult
from sdmx_alignment.semantic_matcher.base import BaseProvider, ProviderError
from sdmx_alignment.semantic_matcher.prompt import SYSTEM_PROMPT, user_prompt


class OpenAIProvider(BaseProvider):
    provider_name = "openai"

    def __init__(self, api_key: str, model: str, timeout: float = 30.0, client=None):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        if client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise ProviderError("The OpenAI client is not installed") from exc
            client = OpenAI(api_key=api_key, timeout=timeout)
        self.client = client

    def is_ready(self) -> ProviderReadiness:
        ready = bool(self.api_key and self.model)
        return ProviderReadiness(ready=ready, message="OpenAI configured" if ready else "OpenAI key and model are required")

    def match(self, request: SemanticMatchRequest) -> SemanticMatchResult:
        if not self.is_ready().ready:
            raise ProviderError(self.is_ready().message)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt(request)},
                ],
            )
            payload = json.loads(response.choices[0].message.content)
            payload.update(provider="openai", model=self.model)
            return SemanticMatchResult.model_validate(payload)
        except Exception as exc:
            raise ProviderError("OpenAI semantic matching failed") from exc

    def recommend(
        self, request: StandardsRecommendationRequest
    ) -> StandardsRecommendationResult:
        if not self.is_ready().ready:
            raise ProviderError(self.is_ready().message)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Recommend SDMX standards alignment using only the supplied JSON. "
                            "Return one JSON object matching the requested result fields. "
                            "Use only supplied local, reference, code, principle, and citation IDs. "
                            "Do not invent evidence or identifiers; abstain when evidence is insufficient."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(request.model_dump(mode="json"), ensure_ascii=True),
                    },
                ],
            )
            payload = json.loads(response.choices[0].message.content)
            payload.update(provider="openai", model=self.model)
            return StandardsRecommendationResult.model_validate(payload)
        except Exception as exc:
            raise ProviderError("OpenAI standards recommendation failed") from exc

    def complete(self, question: str, context: dict) -> str:
        if not self.is_ready().ready:
            raise ProviderError(self.is_ready().message)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                messages=[
                    {
                        "role": "system",
                        "content": "Assess SDMX interoperability using only supplied evidence. Cite element IDs and mark uncertainty.",
                    },
                    {"role": "user", "content": question + "\n\nEvidence:\n" + json.dumps(context, ensure_ascii=True)},
                ],
            )
            return str(response.choices[0].message.content).strip()
        except Exception as exc:
            raise ProviderError("OpenAI assessment generation failed") from exc
