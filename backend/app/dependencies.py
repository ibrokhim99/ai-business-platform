"""FastAPI dependency injection — registry, redis, db, current_user, require_role."""
from __future__ import annotations

from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, Header, Request
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthError, ForbiddenError
from app.core.security import decode_token
from app.db.session import get_db
from app.ml.registry import ModelRegistry, get_registry

# ── Model registry ─────────────────────────────────────────────────────────────

def registry_dep() -> ModelRegistry:
    return get_registry()


RegistryDep = Annotated[ModelRegistry, Depends(registry_dep)]

# ── DB session ─────────────────────────────────────────────────────────────────

DBDep = Annotated[AsyncSession, Depends(get_db)]

# ── Redis ──────────────────────────────────────────────────────────────────────

def redis_dep(request: Request) -> aioredis.Redis | None:
    """Return the app-level Redis client (may be None if Redis is unavailable)."""
    return getattr(request.app.state, "redis", None)


RedisDep = Annotated[aioredis.Redis | None, Depends(redis_dep)]

# ── Auth ───────────────────────────────────────────────────────────────────────

class CurrentUser:
    def __init__(self, user_id: str, email: str, role: str):
        self.user_id = user_id
        self.email = email
        self.role = role


async def get_current_user(authorization: Annotated[str | None, Header()] = None) -> CurrentUser:
    if authorization is None or not authorization.startswith("Bearer "):
        raise AuthError("Missing or malformed Authorization header")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
    except JWTError:
        raise AuthError("Invalid or expired token")
    if payload.get("type") != "access":
        raise AuthError("Invalid token type")
    return CurrentUser(
        user_id=str(payload["sub"]),
        email=payload.get("email", ""),
        role=payload.get("role", "customer"),
    )


UserDep = Annotated[CurrentUser, Depends(get_current_user)]


def require_role(*roles: str):
    """Factory: returns a FastAPI dependency that checks the user has one of the given roles."""
    async def _check(user: UserDep) -> CurrentUser:
        if user.role not in roles:
            raise ForbiddenError(f"Role '{user.role}' not permitted. Required: {list(roles)}")
        return user
    return Depends(_check)
