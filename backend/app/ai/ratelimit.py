"""In-memory per-user rate limiter for AI endpoints.

Note:
    This in-memory rate limiter is intended for a single-process deployment
    and is not shared across multiple workers or server instances. For distributed
    deployments, a persistent/shared store such as Redis should be used.
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, status

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.models import User


class InMemoryAIRateLimiter:
    """Thread-safe sliding window rate limiter tracking requests per user_id."""

    def __init__(
        self,
        max_calls: int | None = None,
        window_seconds: int = 3600,
    ):
        self._max_calls = max_calls
        self._window_seconds = window_seconds
        self._user_timestamps: dict[int, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    @property
    def max_calls(self) -> int:
        if self._max_calls is not None:
            return self._max_calls
        return settings.ai_calls_per_user_per_hour

    @property
    def window_seconds(self) -> int:
        return self._window_seconds

    def check(self, user_id: int) -> None:
        """Check if user has exceeded their rate limit.

        Removes expired timestamps. If limit is exceeded, raises HTTPException 429.
        Otherwise records the timestamp of the current request.
        """
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            queue = self._user_timestamps[user_id]

            # Prune expired timestamps from the rolling window
            while queue and queue[0] <= cutoff:
                queue.popleft()

            if len(queue) >= self.max_calls:
                retry_after = int(queue[0] + self.window_seconds - now) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"AI rate limit exceeded. You may make up to {self.max_calls} "
                        "AI requests per hour. Please try again later."
                    ),
                    headers={"Retry-After": str(max(1, retry_after))},
                )

            queue.append(now)

    def reset(self, user_id: int | None = None) -> None:
        """Reset rate limit history for a specific user or all users (useful in tests)."""
        with self._lock:
            if user_id is not None:
                self._user_timestamps.pop(user_id, None)
            else:
                self._user_timestamps.clear()

    def get_count(self, user_id: int) -> int:
        """Return the current non-expired request count for user_id."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            queue = self._user_timestamps.get(user_id)
            if not queue:
                return 0
            while queue and queue[0] <= cutoff:
                queue.popleft()
            return len(queue)


ai_rate_limiter = InMemoryAIRateLimiter()


def check_ai_rate_limit(
    current_user: User = Depends(get_current_user),
) -> None:
    """FastAPI dependency to enforce AI rate limits per authenticated user."""
    ai_rate_limiter.check(current_user.id)
