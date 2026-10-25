import uuid

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession
from app.core.security import (
    TokenValidationError,
    decode_token,
    hash_password,
    hash_token,
    is_expired,
    verify_password,
)
from app.db.base import utcnow
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.audit import add_audit_log, request_ip
from app.services.auth import issue_token_pair
from app.services.rate_limit import (
    RateLimitUnavailable,
    get_client_ip,
    login_rate_limiter,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


def normalized_email(email: str) -> str:
    return email.strip().lower()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: DbSession) -> User:
    email = normalized_email(str(payload.email))
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")
    user = User(email=email, full_name=payload.full_name, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.flush()
        add_audit_log(
            db,
            action="USER_REGISTERED",
            entity_type="user",
            user_id=user.id,
            entity_id=user.id,
            ip_address=request_ip(request),
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered") from None
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: DbSession) -> TokenResponse:
    try:
        rate_limit = login_rate_limiter.check(get_client_ip(request))
    except RateLimitUnavailable:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Login is temporarily unavailable. Please try again later.",
            headers={"Retry-After": "30"},
        ) from None
    if not rate_limit.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
            headers={"Retry-After": str(rate_limit.retry_after)},
        )

    email = normalized_email(str(payload.email))
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        add_audit_log(
            db,
            action="AUTH_LOGIN_FAILED",
            entity_type="user",
            user_id=user.id if user else None,
            entity_id=user.id if user else None,
            metadata={"reason": "invalid_credentials"},
            ip_address=request_ip(request),
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    tokens = issue_token_pair(db, user)
    add_audit_log(
        db,
        action="AUTH_LOGIN_SUCCEEDED",
        entity_type="user",
        user_id=user.id,
        entity_id=user.id,
        ip_address=request_ip(request),
    )
    db.commit()
    return tokens


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, request: Request, db: DbSession) -> TokenResponse:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid, expired, or revoked refresh token",
    )
    try:
        claims = decode_token(payload.refresh_token, "refresh")
        token_id = uuid.UUID(claims["jti"])
        user_id = uuid.UUID(claims["sub"])
    except (TokenValidationError, ValueError, KeyError):
        raise unauthorized from None

    stored = db.scalar(
        select(RefreshToken).where(RefreshToken.id == token_id).with_for_update()
    )
    if (
        stored is None
        or stored.user_id != user_id
        or stored.token_hash != hash_token(payload.refresh_token)
        or stored.revoked_at is not None
        or is_expired(stored.expires_at)
    ):
        raise unauthorized
    user = db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    if user is None:
        raise unauthorized

    tokens = issue_token_pair(db, user)
    stored.revoked_at = utcnow()
    stored.replaced_by_id = uuid.UUID(decode_token(tokens.refresh_token, "refresh")["jti"])
    add_audit_log(
        db,
        action="AUTH_TOKEN_REFRESHED",
        entity_type="user",
        user_id=user.id,
        entity_id=user.id,
        ip_address=request_ip(request),
    )
    db.commit()
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: LogoutRequest, request: Request, db: DbSession) -> Response:
    try:
        claims = decode_token(payload.refresh_token, "refresh")
        token_id = uuid.UUID(claims["jti"])
    except (TokenValidationError, ValueError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from None
    stored = db.scalar(
        select(RefreshToken).where(RefreshToken.id == token_id).with_for_update()
    )
    if stored is not None and stored.token_hash == hash_token(payload.refresh_token):
        if stored.revoked_at is None:
            stored.revoked_at = utcnow()
            add_audit_log(
                db,
                action="AUTH_LOGGED_OUT",
                entity_type="user",
                user_id=stored.user_id,
                entity_id=stored.user_id,
                ip_address=request_ip(request),
            )
            db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserResponse)
def me(current_user: CurrentUser) -> User:
    return current_user
