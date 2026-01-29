"""HTTP API client demonstrating network dependency patterns.

This module shows a typical API client that makes HTTP requests. Tests for this
code often become flaky because they hit real endpoints that may be:
- Slow or unavailable
- Rate-limited
- Returning different data over time
- Behind authentication that expires

The solution is to mock HTTP calls in small tests using libraries like:
- pytest-httpx (for httpx)
- responses (for requests)
- respx (for httpx with respx)
- httpretty (general-purpose)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
)

if TYPE_CHECKING:
    from collections.abc import Callable

# Using a simple urllib-based client to avoid external dependencies
import json
import urllib.request


@dataclass
class User:
    """A user from the API."""

    id: int
    name: str
    email: str


class ApiClient:
    """HTTP client for the user API.

    This is a simple client that demonstrates the network dependency problem.
    In production, you'd use httpx or requests.
    """

    def __init__(
        self,
        base_url: str,
        http_get: Callable[[str], Any] | None = None,
    ) -> None:
        """Initialize the API client.

        Args:
            base_url: Base URL for the API (e.g., 'https://api.example.com').
            http_get: Optional HTTP GET function for dependency injection.
                     If not provided, uses real HTTP requests.

        """
        self.base_url = base_url.rstrip("/")
        self._http_get = http_get or self._real_http_get

    def _real_http_get(self, url: str) -> Any:
        """Make a real HTTP GET request.

        This is what causes flaky tests - it hits the real network.
        Returns the parsed JSON, which could be a dict, list, or primitive.
        """
        with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310
            return json.loads(response.read().decode())

    def get_user(self, user_id: int) -> User:
        """Fetch a user by ID.

        Args:
            user_id: The user's ID.

        Returns:
            The User object.

        Raises:
            ConnectionError: If the API is unavailable.
            ValueError: If the user is not found.

        """
        url = f"{self.base_url}/users/{user_id}"
        data = self._http_get(url)
        return User(
            id=data["id"],
            name=data["name"],
            email=data.get("email", ""),
        )

    def list_users(self) -> list[User]:
        """List all users.

        Returns:
            List of User objects.

        """
        url = f"{self.base_url}/users"
        data = self._http_get(url)
        return [User(id=u["id"], name=u["name"], email=u.get("email", "")) for u in data]

    def health_check(self) -> bool:
        """Check if the API is healthy.

        Returns:
            True if the API is healthy, False otherwise.

        """
        try:
            url = f"{self.base_url}/health"
            data = self._http_get(url)
            return data.get("status") == "ok"
        except Exception:  # noqa: BLE001
            return False
