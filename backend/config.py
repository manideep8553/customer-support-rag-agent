from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    app_name: str = "GigaCorp Customer Support RAG Agent"
    app_version: str = "1.0.0"

    knowledge_base_path: Path = Path("data/knowledge_base")
    vector_store_path: Path = Path("data/vector_store")

    chunk_size: int = 512
    chunk_overlap: int = 64
    top_k_retrieval: int = 4
    similarity_threshold: float = 0.45

    vector_store_type: str = "faiss"

    embedding_provider: str = "huggingface"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384

    llm_provider: str = ""
    llm_model: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    memory_backend: str = "langgraph_state"

    memory_max_turns: int = 20
    session_timeout_minutes: int = 60
    max_history_tokens: int = 2048
    summarization_threshold_turns: int = 20

    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
