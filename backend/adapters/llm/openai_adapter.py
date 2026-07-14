import logging
from typing import AsyncIterator

from backend.config import settings
from backend.errors import log_exception, retry
from backend.ports.llm import LLM

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
            from openai import AsyncOpenAI, OpenAI
            self._client = OpenAI(api_key=self.api_key, timeout=30)
            self._async_client = AsyncOpenAI(api_key=self.api_key, timeout=30)
        except ImportError:
            logger.warning("openai package not installed. Install: pip install openai")
        except Exception as e:
            logger.error("Failed to initialize OpenAI client: %s", e)
            log_exception(e, "OpenAIAdapter._init")

    @retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(Exception,))
    def _call_generate(self, messages: list[dict]) -> str:
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            max_tokens=1024,
            timeout=30,
        )
        return resp.choices[0].message.content or ""

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        if self._client is None:
            logger.error("OpenAI client not initialized")
            return "I'm sorry, the AI service is not available right now. Please try again later."
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            return self._call_generate(messages)
        except Exception as e:
            log_exception(e, "OpenAIAdapter.generate")
            return (
                "I'm sorry, I encountered a temporary issue while generating a response. "
                "Please try again in a moment."
            )

    async def stream(self, prompt: str, system_prompt: str | None = None) -> AsyncIterator[str]:
        if self._async_client is None:
            logger.error("OpenAI async client not initialized")
            yield "I'm sorry, the AI service is not available right now. Please try again later."
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
                timeout=30,
            )
            async for chunk in stream:
                token = chunk.choices[0].delta.content or ""
                if token:
                    yield token
        except Exception as e:
            log_exception(e, "OpenAIAdapter.stream")
            yield (
                "I'm sorry, I encountered a temporary issue while streaming a response. "
                "Please try again in a moment."
            )

    def count_tokens(self, text: str) -> int:
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except ImportError:
            return len(text.split())
