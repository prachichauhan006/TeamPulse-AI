"""Redis-backed fixed-window rate limits with local-only memory fallback."""

import hashlib
import ipaddress
import math
import threading
import time
from dataclasses import dataclass

import redis
from fastapi import Request

from app.core.config import get_settings

LOGIN_RATE_LIMIT = 5
AI_RATE_LIMIT = 10
SEARCH_RATE_LIMIT = 30
RATE_LIMIT_WINDOW_SECONDS = 60
# Backward-compatible name used by the original login implementation.
LOGIN_RATE_WINDOW_SECONDS = RATE_LIMIT_WINDOW_SECONDS


class RateLimitUnavailable(RuntimeError):
    """Raised when production cannot enforce its Redis-backed limit."""


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after: int = 0


def get_client_ip(request: Request) -> str:
    """Return the direct peer unless trusted proxy headers are explicitly enabled."""
    direct_ip = request.client.host if request.client else "unknown"
    if not get_settings().trust_proxy_headers:
        return direct_ip

    forwarded_for = request.headers.get("x-forwarded-for", "")
    candidate = forwarded_for.split(",", 1)[0].strip()
    if not candidate:
        candidate = request.headers.get("x-real-ip", "").strip()
    if candidate:
        try:
            return str(ipaddress.ip_address(candidate))
        except ValueError:
            pass
    return direct_ip


def rate_limit_key(identity: str, scope: str = "login") -> str:
    # Avoid raw identities and user-controlled characters in Redis keys.
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    return f"teampulse:rate-limit:{scope}:{digest}"


class InMemoryRateLimiter:
    """Process-local limiter for tests and development fallback only."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self._limit = limit
        self._window_seconds = window_seconds
        self._windows: dict[str, tuple[float, int]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> RateLimitDecision:
        now = time.monotonic()
        with self._lock:
            self._prune_expired(now)
            window_start, count = self._windows.get(key, (now, 0))
            if now - window_start >= self._window_seconds:
                window_start, count = now, 0
            count += 1
            self._windows[key] = (window_start, count)
            retry_after = max(1, math.ceil(window_start + self._window_seconds - now))
            if count <= self._limit:
                return RateLimitDecision(allowed=True)
            return RateLimitDecision(allowed=False, retry_after=retry_after)

    def reset(self) -> None:
        with self._lock:
            self._windows.clear()

    def _prune_expired(self, now: float) -> None:
        if len(self._windows) < 5_000:
            return
        expired = [
            key
            for key, (window_start, _) in self._windows.items()
            if now - window_start >= self._window_seconds
        ]
        for key in expired:
            self._windows.pop(key, None)


class RedisRateLimiter:
    def __init__(self, redis_url: str, limit: int, window_seconds: int) -> None:
        self._limit = limit
        self._window_seconds = window_seconds
        self._client = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
            health_check_interval=30,
        )

    def check(self, key: str) -> RateLimitDecision:
        # MULTI/EXEC keeps the counter and initial expiry together. NX preserves
        # the original window expiry on subsequent requests.
        with self._client.pipeline(transaction=True) as pipeline:
            pipeline.incr(key)
            pipeline.expire(key, self._window_seconds, nx=True)
            count, _ = pipeline.execute()
        if count <= self._limit:
            return RateLimitDecision(allowed=True)
        ttl = self._client.ttl(key)
        return RateLimitDecision(
            allowed=False,
            retry_after=ttl if ttl > 0 else self._window_seconds,
        )


class RateLimiter:
    def __init__(self, scope: str, limit: int, window_seconds: int = RATE_LIMIT_WINDOW_SECONDS) -> None:
        self._settings = get_settings()
        self._scope = scope
        self._memory = InMemoryRateLimiter(limit, window_seconds)
        self._redis: RedisRateLimiter | None = None
        self._limit = limit
        self._window_seconds = window_seconds

    def check(self, identity: str) -> RateLimitDecision:
        key = rate_limit_key(identity, self._scope)
        # Tests deliberately use isolated process-local state, even if a real
        # Redis service happens to be running on the development machine.
        if self._settings.app_env == "test":
            return self._memory.check(key)
        try:
            if self._redis is None:
                self._redis = RedisRateLimiter(
                    self._settings.redis_url, self._limit, self._window_seconds
                )
            return self._redis.check(key)
        except (redis.RedisError, ValueError) as exc:
            if self._settings.app_env == "production":
                # Never silently disable limiting or use per-process memory in
                # a multi-instance production deployment.
                raise RateLimitUnavailable from exc
            return self._memory.check(key)

    def reset_for_tests(self) -> None:
        if self._settings.app_env != "test":
            raise RuntimeError("Rate-limit reset is available only in tests")
        self._memory.reset()


login_rate_limiter = RateLimiter("login", LOGIN_RATE_LIMIT)
ai_user_rate_limiter = RateLimiter("authenticated-ai", AI_RATE_LIMIT)
search_user_rate_limiter = RateLimiter("authenticated-search", SEARCH_RATE_LIMIT)
