from __future__ import annotations
import os
import requests
from typing import Optional, Any, Dict

from .base import LLMResponse, LLMUsage


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.base_url = (base_url or os.getenv("GEMINI_BASE_URL") or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")

        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) is not set")

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

        # Gemini model örn: "gemini-1.5-flash" gibi
        url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"

        parts = []
        if system:
            parts.append({"text": f"[SYSTEM]\n{system}"})
        parts.append({"text": prompt})

        body: Dict[str, Any] = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        r = requests.post(url, json=body, timeout=60)
        if r.status_code >= 400:
            raise RuntimeError(f"Gemini error {r.status_code}: {r.text}")

        data = r.json()

        # En yaygın cevap formatı:
        candidates = data.get("candidates") or []
        if not candidates:
            raise RuntimeError(f"Gemini empty response: {data}")

        text = candidates[0]["content"]["parts"][0]["text"]

        return LLMResponse(
            text=text,
            model=model,
            provider=self.name,
            usage=None,
            raw=data,
        )
