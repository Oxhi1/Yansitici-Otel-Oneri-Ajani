from __future__ import annotations
import json
from typing import Optional
from .base import LLMResponse, LLMUsage


class MockProvider:
    name = "mock"

    def generate(
        self,
        *,
        system: Optional[str],
        prompt: str,
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 800,
        response_format: Optional[str] = None,
    ) -> LLMResponse:

        # İstersen burada prompt içeriğine göre branch yapabilirsin.
        if response_format == "json":
            payload = {
                "ok": True,
                "note": "mock response",
                "summary": prompt[:120],
            }
            text = json.dumps(payload, ensure_ascii=False)
        else:
            text = f"[MOCK:{model}] {prompt[:200]}"

        return LLMResponse(
            text=text,
            model=model,
            provider=self.name,
            usage=LLMUsage(prompt_tokens=None, completion_tokens=None, total_tokens=None),
            raw=None,
        )
