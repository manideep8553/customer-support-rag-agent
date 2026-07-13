import logging

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
            self._client = OpenAI(api_key=self._api_key)
        except ImportError:
            logger.warning("openai package not installed. Install with: pip install openai")

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self._client is None:
            return [[0.0] * self._dimension for _ in texts]
        try:
            resp = self._client.embeddings.create(model=self.model_name, input=texts)
            return [item.embedding for item in resp.data]
        except Exception as e:
            logger.error("OpenAI embedding error: %s", e)
            return [[0.0] * self._dimension for _ in texts]

    @property
    def dimension(self) -> int:
        return self._dimension
