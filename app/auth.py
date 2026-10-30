"""Authentication and authorization dependencies supporting API keys and service tokens."""

from typing import Annotated

from config import settings
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticatedUser:
    def __init__(self, identity: str, roles: list[str]):
        self.identity = identity
        self.roles = roles

    def has_role(self, role: str) -> bool:
        return role in self.roles or "admin" in self.roles


def get_current_user(
    api_key: Annotated[str | None, Security(api_key_header)] = None,
    bearer: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)] = None,
) -> AuthenticatedUser:
    """Validates authentication credentials if AUTH_ENABLED is set."""
    if not settings.auth_enabled:
        return AuthenticatedUser(identity="anonymous", roles=["admin", "user"])

    if api_key and settings.api_key and api_key == settings.api_key:
        return AuthenticatedUser(identity="service-account", roles=["service", "admin"])

    if bearer and settings.api_key and bearer.credentials == settings.api_key:
        return AuthenticatedUser(identity="bearer-user", roles=["user", "admin"])

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication credentials",
        headers={"WWW-Authenticate": "Bearer, ApiKey"},
    )


def require_role(role: str):
    def role_dependency(user: Annotated[AuthenticatedUser, Depends(get_current_user)]):
        if not user.has_role(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires '{role}' permission",
            )
        return user

    return role_dependency
