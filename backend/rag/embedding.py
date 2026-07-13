import pickle
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from pathlib import Path
from typing import Optional

from backend.config import settings


class EmbeddingService:
    _instance = None
    _vectorizer: Optional[TfidfVectorizer] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _get_vectorizer(self) -> TfidfVectorizer:
        if self._vectorizer is None:
            self._vectorizer = TfidfVectorizer(
                max_features=5000,
                stop_words="english",
                ngram_range=(1, 2),
                sublinear_tf=True,
            )
        return self._vectorizer

    def fit(self, texts: list[str]):
        vectorizer = self._get_vectorizer()
        vectorizer.fit(texts)

    def embed(self, texts: list[str]) -> np.ndarray:
        vectorizer = self._get_vectorizer()
        matrix = vectorizer.transform(texts)
        return matrix.toarray()

    def embed_query(self, text: str) -> np.ndarray:
        vectorizer = self._get_vectorizer()
        vec = vectorizer.transform([text])
        return vec.toarray()[0]

    def embed_sparse(self, texts: list[str]) -> csr_matrix:
        vectorizer = self._get_vectorizer()
        return vectorizer.transform(texts)

    def save(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)
        if self._vectorizer:
            with open(path / "vectorizer.pkl", "wb") as f:
                pickle.dump(self._vectorizer, f)

    def load(self, path: Path):
        pkl_path = path / "vectorizer.pkl"
        if pkl_path.exists():
            with open(pkl_path, "rb") as f:
                self._vectorizer = pickle.load(f)

    @property
    def is_fitted(self) -> bool:
        return self._vectorizer is not None and hasattr(self._vectorizer, "vocabulary_")
