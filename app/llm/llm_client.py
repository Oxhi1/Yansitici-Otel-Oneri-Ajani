from __future__ import annotations
import os
from typing import Optional

from .providers.mock_provider import MockProvider
from .providers.gemini_provider import GeminiProvider
from .providers.base import LLMResponse


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def get_provider():
    provider_name = _env("LLM_PROVIDER", "mock").lower()

    try:
        if provider_name == "mock":
            return MockProvider()
        if provider_name == "gemini":
            return GeminiProvider()
        raise ValueError(f"Unknown LLM_PROVIDER='{provider_name}'. Use mock|gemini.")
    except Exception as e:
        # Demo asla çökmesin
        print(f"⚠️ LLM provider init failed ({provider_name}): {e}")
        print("➡️ Falling back to mock provider.")
        return MockProvider()


def generate_text(
    *,
    prompt: str,
    system: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 800,
    response_format: Optional[str] = None,
) -> LLMResponse:
    provider = get_provider()

    resolved_model = model or _env("LLM_MODEL", "")
    if not resolved_model:
        resolved_model = "gemini-1.5-flash" if provider.name == "gemini" else "mock-model"

    return provider.generate(
        system=system,
        prompt=prompt,
        model=resolved_model,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format=response_format,
    )
