import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import TokenValidationError, decode_token
from app.db.session import get_db
from app.models.enums import WorkspaceRole
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.services.rate_limit import (
    RateLimiter,
    RateLimitUnavailable,
    ai_user_rate_limiter,
    search_user_rate_limiter,
)

bearer_scheme = HTTPBearer(auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized
    try:
        payload = decode_token(credentials.credentials, "access")
        user_id = uuid.UUID(payload["sub"])
    except (TokenValidationError, ValueError, KeyError):
        raise unauthorized from None
    user = db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    if user is None:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def _enforce_user_rate_limit(current_user: User, limiter: RateLimiter) -> None:
    try:
        decision = limiter.check(str(current_user.id))
    except RateLimitUnavailable:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is temporarily unavailable. Please try again later.",
            headers={"Retry-After": "30"},
        ) from None
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(decision.retry_after)},
        )


def enforce_ai_rate_limit(current_user: CurrentUser) -> None:
    _enforce_user_rate_limit(current_user, ai_user_rate_limiter)


def enforce_search_rate_limit(current_user: CurrentUser) -> None:
    _enforce_user_rate_limit(current_user, search_user_rate_limiter)


def get_membership(workspace_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> WorkspaceMember:
    membership = db.scalar(
        select(WorkspaceMember)
        .join(Workspace, Workspace.id == WorkspaceMember.workspace_id)
        .where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_user.id,
            Workspace.deleted_at.is_(None),
        )
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace access denied")
    return membership


CurrentMembership = Annotated[WorkspaceMember, Depends(get_membership)]


def require_roles(*roles: WorkspaceRole) -> Callable:
    allowed = set(roles)

    def role_dependency(membership: CurrentMembership) -> WorkspaceMember:
        if membership.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient workspace permissions",
            )
        return membership

    return role_dependency
