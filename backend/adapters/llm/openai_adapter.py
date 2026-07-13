import json
import logging
from typing import AsyncIterator

from backend.ports.llm import LLM
from backend.config import settings

logger = logging.getLogger("gigacorp.llm.openai")


class OpenAIAdapter(LLM):
    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None):
        self.model = model
        self.api_key = api_key or settings.openai_api_key
        self._client = None
        self._async_client = None
        self._init()

    def _init(self):
        try:
            from openai import OpenAI, AsyncOpenAI
            self._client = OpenAI(api_key=self.api_key)
            self._async_client = AsyncOpenAI(api_key=self.api_key)
        except ImportError:
            logger.warning("openai package not installed. Install: pip install openai")

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        if self._client is None:
            return "[OpenAI SDK not available]"
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=1024,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            logger.error("OpenAI generate error: %s", e)
            return f"[OpenAI error: {e}]"

    async def stream(self, prompt: str, system_prompt: str | None = None) -> AsyncIterator[str]:
        if self._async_client is None:
            yield "[OpenAI SDK not available]"
            return
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            stream = await self._async_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=1024,
                stream=True,
            )
            async for chunk in stream:
                token = chunk.choices[0].delta.content or ""
                if token:
                    yield token
        except Exception as e:
            logger.error("OpenAI stream error: %s", e)
            yield f"[OpenAI error: {e}]"

    def count_tokens(self, text: str) -> int:
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except ImportError:
            return len(text.split())
