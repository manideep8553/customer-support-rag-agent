import json
import logging
import httpx
from typing import AsyncIterator

from backend.ports.llm import LLM
from backend.config import settings
from backend.errors import LLMError, log_exception, retry

logger = logging.getLogger("gigacorp.llm.ollama")


class OllamaAdapter(LLM):
    def __init__(self, model: str = "llama3.1:8b", base_url: str = "http://localhost:11434"):
        self.model = settings.llm_model if hasattr(settings, 'llm_model') else model
        self.base_url = base_url

    @retry(max_attempts=2, delay=2.0, backoff=2.0, exceptions=(httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError))
    def _call_generate(self, payload: dict) -> str:
        with httpx.Client(timeout=60) as client:
            resp = client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            return resp.json().get("response", "")

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 1024},
        }
        if system_prompt:
            payload["system"] = system_prompt
        try:
            return self._call_generate(payload)
        except httpx.TimeoutException as e:
            logger.error("Ollama request timed out for model %s: %s", self.model, e)
            return (
                "I'm sorry, the AI service is taking too long to respond. "
                "Please try again later or contact support if the issue persists."
            )
        except httpx.HTTPStatusError as e:
            logger.error("Ollama returned HTTP %s for model %s: %s", e.response.status_code, self.model, e)
            return (
                "I'm sorry, the AI service encountered an error. "
                "Please try again later."
            )
        except Exception as e:
            log_exception(e, "OllamaAdapter.generate")
            return (
                "I'm sorry, I encountered a temporary issue while generating a response. "
                "Please try again in a moment."
            )

    @retry(max_attempts=2, delay=2.0, backoff=2.0, exceptions=(httpx.TimeoutException, httpx.ConnectError))
    async def _call_stream(self, payload: dict):
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", f"{self.base_url}/api/generate", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            token = data.get("response", "")
                            if token:
                                yield token
                        except json.JSONDecodeError:
                            continue

    async def stream(self, prompt: str, system_prompt: str | None = None) -> AsyncIterator[str]:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {"num_predict": 1024},
        }
        if system_prompt:
            payload["system"] = system_prompt
        try:
            async for token in self._call_stream(payload):
                yield token
        except httpx.TimeoutException as e:
            logger.error("Ollama stream timed out: %s", e)
            yield (
                "I'm sorry, the AI service is taking too long to respond. "
                "Please try again later."
            )
        except httpx.HTTPStatusError as e:
            logger.error("Ollama stream HTTP error: %s", e)
            yield "I'm sorry, the AI service encountered an error. Please try again later."
        except Exception as e:
            log_exception(e, "OllamaAdapter.stream")
            yield (
                "I'm sorry, I encountered a temporary issue while generating a response. "
                "Please try again in a moment."
            )

    def count_tokens(self, text: str) -> int:
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except ImportError:
            return len(text.split())
