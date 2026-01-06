from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Protocol


@dataclass
class LLMUsage:
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


@dataclass
class LLMResponse:
    text: str
    model: str
    provider: str
    usage: Optional[LLMUsage] = None
    raw: Optional[Any] = None


class LLMProvider(Protocol):
    """
    Provider interface. Concrete providers (mock/gemini/etc.) must implement `generate`.
    """
    name: str

    def generate(
        self,
        *,
        system: Optional[str],
        prompt: str,
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 800,
        response_format: Optional[str] = None,  # e.g. "json"
    ) -> LLMResponse:
        ...
