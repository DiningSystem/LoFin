from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from lofin.core.config import Settings, get_settings


class OllamaClient:
    """Async client for local Ollama chat, generation, streaming, and embeddings."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = httpx.AsyncClient(base_url=self.settings.ollama_base_url, timeout=self.settings.llm_timeout_seconds)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4))
    async def generate_json(self, prompt: str, model: str | None = None) -> dict[str, Any]:
        response = await self.client.post(
            "/api/generate",
            json={"model": model or self.settings.ollama_model, "prompt": prompt, "stream": False, "format": "json"},
        )
        response.raise_for_status()
        payload = response.json()
        text = payload.get("response", "{}")
        return json.loads(text)

    async def stream(self, prompt: str, model: str | None = None) -> AsyncIterator[str]:
        async with self.client.stream(
            "POST",
            "/api/generate",
            json={"model": model or self.settings.ollama_model, "prompt": prompt, "stream": True},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    yield data.get("response", "")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4))
    async def embed(self, text: str) -> list[float]:
        response = await self.client.post("/api/embeddings", json={"model": self.settings.ollama_embed_model, "prompt": text})
        response.raise_for_status()
        return list(response.json().get("embedding", []))

    async def close(self) -> None:
        await self.client.aclose()
