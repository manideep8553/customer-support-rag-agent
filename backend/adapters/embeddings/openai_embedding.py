import logging

from backend.errors import EmbeddingError, log_exception, retry

logger = logging.getLogger("gigacorp.embeddings")


class OpenAIEmbedding:
    def __init__(self, model_name: str = "text-embedding-3-small", api_key: str | None = None):
        self.model_name = model_name
        self._client = None
        self._api_key = api_key
        self._dimension: int = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }.get(model_name, 1536)
        self._load()

    def _load(self) -> None:
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key, timeout=30)
        except ImportError:
            logger.warning("openai package not installed. Install with: pip install openai")

    @retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(Exception,))
    def _call_embeddings(self, texts: list[str]) -> list[list[float]]:
        resp = self._client.embeddings.create(model=self.model_name, input=texts)
        return [item.embedding for item in resp.data]

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self._client is None:
            logger.warning("OpenAI client not available, returning zero vectors")
            return [[0.0] * self._dimension for _ in texts]
        try:
            return self._call_embeddings(texts)
        except Exception as e:
            log_exception(e, "OpenAIEmbedding.embed")
            raise EmbeddingError("Failed to generate embeddings with OpenAI", cause=e)

    @property
    def dimension(self) -> int:
        return self._dimension
