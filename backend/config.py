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
    similarity_threshold: float = 0.28

    vector_store_type: str = "faiss"

    embedding_provider: str = "huggingface"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384

    api_key: str = ""

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

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/gigacorp"
    database_echo: bool = False
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # JWT
    jwt_secret_key: str = "change-me-to-a-secure-random-string-at-least-32-chars"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
