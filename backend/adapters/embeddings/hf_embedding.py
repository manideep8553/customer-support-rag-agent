import logging

logger = logging.getLogger("gigacorp.embeddings")


class HFEmbedding:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._dimension: int = 384

    def _lazy_load(self):
        if self._model is not None:
            return
        try:
            from fastembed import TextEmbedding
            logger.info("Loading embedding model: %s", self.model_name)
            self._model = TextEmbedding(model_name=self.model_name, max_length=512)
            self._dimension = self._model.embedding_size
        except ImportError:
            logger.warning(
                "fastembed not installed. Install with: pip install fastembed"
            )

    def embed(self, texts: list[str]) -> list[list[float]]:
        self._lazy_load()
        if self._model is None:
            return [[0.0] * self._dimension for _ in texts]
        embeddings = list(self._model.embed(texts))
        return [e.tolist() for e in embeddings]

    @property
    def dimension(self) -> int:
        self._lazy_load()
        return self._dimension
