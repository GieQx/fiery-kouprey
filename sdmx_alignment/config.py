from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, Field


def choose_ollama_model(models: list[str], configured: str = "") -> str:
    if configured in models:
        return configured
    return models[0] if models else ""


class LLMSettings(BaseModel):
    provider: Literal["none", "openai", "ollama"] = "none"
    openai_api_key: str = ""
    openai_model: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = ""
    timeout_seconds: float = Field(default=30.0, ge=1.0, le=180.0)

    @classmethod
    def from_env(cls):
        provider = os.getenv("LLM_PROVIDER", "none").casefold()
        if provider not in {"none", "openai", "ollama"}:
            provider = "none"
        return cls(
            provider=provider,
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", ""),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", ""),
            timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
        )
