from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class User:
    id: str
    email: str
    name: str
    roles: list[str]


@dataclass
class AuthToken:
    token: str
    user_id: str
    expires_at: int


class AuthProvider(Protocol):
    async def authenticate(self, token: str) -> Optional[User]: ...

    async def create_token(self, user: User) -> AuthToken: ...

    async def validate_api_key(self, api_key: str) -> Optional[User]: ...

    async def get_user(self, user_id: str) -> Optional[User]: ...


class PermissionChecker(Protocol):
    def require_role(self, role: str) -> bool: ...

    def require_any_role(self, roles: list[str]) -> bool: ...
