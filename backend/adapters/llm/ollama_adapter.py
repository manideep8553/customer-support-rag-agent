import json
import httpx
from typing import AsyncIterator

from backend.ports.llm import LLM
from backend.config import settings


class OllamaAdapter(LLM):
    def __init__(self, model: str = "llama3.1:8b", base_url: str = "http://localhost:11434"):
        self.model = settings.llm_model if hasattr(settings, 'llm_model') else model
        self.base_url = base_url

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt
        try:
            resp = httpx.post(f"{self.base_url}/api/generate", json=payload, timeout=60)
            resp.raise_for_status()
            return resp.json().get("response", "")
        except Exception as e:
            return f"[Ollama error: {e}]"

    async def stream(self, prompt: str, system_prompt: str | None = None) -> AsyncIterator[str]:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
        }
        if system_prompt:
            payload["system"] = system_prompt
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", f"{self.base_url}/api/generate", json=payload, timeout=60) as resp:
                async for line in resp.aiter_lines():
                    if line.strip():
                        data = json.loads(line)
                        token = data.get("response", "")
                        if token:
                            yield token

    def count_tokens(self, text: str) -> int:
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except ImportError:
            return len(text.split())
