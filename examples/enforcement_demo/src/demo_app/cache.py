"""TTL-based cache demonstrating time/sleep dependency patterns.

This module shows a cache implementation with time-to-live (TTL) expiration.
Tests for TTL logic often become flaky because they:
- Use time.sleep() to wait for expiration
- Are sensitive to system clock variations
- Take a long time to run

The solution is to inject time as a dependency:
- Accept a `time_func` parameter (defaults to time.time)
- In tests, provide a controllable fake time
- Or use freezegun/time-machine for global time control
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import (
    dataclass,
    field,
)
from typing import (
    Any,
)


@dataclass
class CacheEntry:
    """A cache entry with expiration time."""

    value: Any
    expires_at: float


@dataclass
class Cache:
    """Simple in-memory cache with TTL support.

    The cache supports time-based expiration and can be configured
    with a custom time function for testability.
    """

    default_ttl: float = 60.0
    time_func: Callable[[], float] = field(default_factory=lambda: time.time)
    _entries: dict[str, CacheEntry] = field(default_factory=dict)

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Store a value in the cache.

        Args:
            key: Cache key.
            value: Value to store.
            ttl: Time-to-live in seconds. Uses default_ttl if not specified.

        """
        actual_ttl = ttl if ttl is not None else self.default_ttl
        expires_at = self.time_func() + actual_ttl
        self._entries[key] = CacheEntry(value=value, expires_at=expires_at)

    def get(self, key: str) -> Any | None:
        """Retrieve a value from the cache.

        Args:
            key: Cache key.

        Returns:
            The cached value, or None if not found or expired.

        """
        entry = self._entries.get(key)
        if entry is None:
            return None

        if self.time_func() >= entry.expires_at:
            # Entry has expired, remove it
            del self._entries[key]
            return None

        return entry.value

    def delete(self, key: str) -> bool:
        """Delete a value from the cache.

        Args:
            key: Cache key.

        Returns:
            True if the key existed, False otherwise.

        """
        if key in self._entries:
            del self._entries[key]
            return True
        return False

    def clear(self) -> None:
        """Remove all entries from the cache."""
        self._entries.clear()

    def cleanup_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries removed.

        """
        now = self.time_func()
        expired_keys = [key for key, entry in self._entries.items() if now >= entry.expires_at]
        for key in expired_keys:
            del self._entries[key]
        return len(expired_keys)


def wait_for_expiration(seconds: float) -> None:
    """Wait for cache entries to expire.

    This is the WRONG way to test TTL - it wastes time and is flaky.
    It's here only to demonstrate the anti-pattern.

    Args:
        seconds: Number of seconds to wait.

    """
    time.sleep(seconds)
