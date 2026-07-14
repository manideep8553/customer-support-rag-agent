from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "GigaCorp Customer Support RAG Agent"
    app_version: str = "2.0.0"
    environment: str = "development"
    debug: bool = True

    knowledge_base_path: Path = Path("data/knowledge_base")
    vector_store_path: Path = Path("data/vector_store")
    upload_dir: Path = Path("data/uploads")

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
    reload: bool = False

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

    # Enterprise: Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_db: int = 1
    redis_rate_limit_db: int = 2
    redis_job_db: int = 3
    redis_socket_timeout: int = 5

    # Enterprise: Caching
    cache_enabled: bool = True
    cache_default_ttl_seconds: int = 300
    cache_embedding_ttl_seconds: int = 3600
    cache_response_ttl_seconds: int = 600
    cache_max_size: int = 5000

    # Enterprise: Rate Limiting
    rate_limiting_enabled: bool = True
    rate_limit_chat_per_minute: int = 30
    rate_limit_chat_per_hour: int = 500
    rate_limit_ingest_per_minute: int = 10
    rate_limit_auth_per_minute: int = 20

    # Enterprise: Email
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    email_from_name: str = "GigaCorp Support"
    email_from_address: str = "support@gigacorp.com"
    email_enabled: bool = False

    # Enterprise: Notifications
    notification_enabled: bool = True
    notification_ws_ping_interval: int = 30
    notification_ws_ping_timeout: int = 10

    # Enterprise: File Storage
    file_storage_backend: str = "local"
    s3_bucket: str = ""
    s3_region: str = "us-east-1"
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_endpoint_url: Optional[str] = None
    max_upload_size_mb: int = 50
    allowed_upload_extensions: str = ".jpg,.jpeg,.png,.gif,.pdf,.doc,.docx,.xls,.xlsx,.csv,.txt,.zip"

    # Enterprise: Background Jobs
    job_queue_url: str = "redis://localhost:6379/3"
    job_concurrency: int = 4
    job_max_retries: int = 3
    job_retry_delay_seconds: int = 60

    # Enterprise: Logging
    log_level: str = "INFO"
    log_format: str = "text"
    log_file: str = "logs/gigacorp.log"
    log_file_max_size_mb: int = 100
    log_file_backup_count: int = 10
    sentry_dsn: Optional[str] = None

    # Enterprise: Monitoring
    metrics_enabled: bool = True
    metrics_port: int = 9090
    health_check_interval_seconds: int = 30

    # Enterprise: Audit
    audit_enabled: bool = True
    audit_log_table: str = "audit_logs"
    audit_log_body_max_length: int = 10000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
