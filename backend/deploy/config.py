from dataclasses import dataclass, field
from typing import Any


@dataclass
class DeploymentProfile:
    name: str
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    log_level: str = "INFO"
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    api_key_required: bool = False
    ssl_enabled: bool = False
    ssl_cert_path: str = ""
    ssl_key_path: str = ""
    rate_limit_requests: int = 60
    rate_limit_window: int = 60
    vector_store_type: str = "faiss"
    memory_backend: str = "langgraph_state"
    auto_migrate: bool = True
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "workers": self.workers,
            "log_level": self.log_level,
            "cors_origins": self.cors_origins,
            "api_key_required": self.api_key_required,
            "ssl_enabled": self.ssl_enabled,
            "rate_limit_requests": self.rate_limit_requests,
            "rate_limit_window": self.rate_limit_window,
            "vector_store_type": self.vector_store_type,
        }


PROFILES: dict[str, DeploymentProfile] = {
    "development": DeploymentProfile(
        name="development",
        host="0.0.0.0",
        port=8000,
        log_level="DEBUG",
        cors_origins=["*"],
        api_key_required=False,
    ),
    "production": DeploymentProfile(
        name="production",
        host="0.0.0.0",
        port=8000,
        workers=4,
        log_level="INFO",
        cors_origins=["https://app.gigacorp.com"],
        api_key_required=True,
        rate_limit_requests=30,
    ),
    "staging": DeploymentProfile(
        name="staging",
        host="0.0.0.0",
        port=8080,
        workers=2,
        log_level="DEBUG",
        cors_origins=["https://staging.gigacorp.com"],
        api_key_required=True,
    ),
}


def get_profile(name: str = "development") -> DeploymentProfile:
    return PROFILES.get(name, PROFILES["development"])


def configure_from_profile(profile: DeploymentProfile):
    from backend.config import settings
    settings.host = profile.host
    settings.port = profile.port
    if profile.vector_store_type:
        settings.vector_store_type = profile.vector_store_type
    if profile.memory_backend:
        settings.memory_backend = profile.memory_backend
