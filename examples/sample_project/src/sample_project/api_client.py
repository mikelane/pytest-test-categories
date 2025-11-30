"""HTTP API client for external service integration.

This module demonstrates a typical HTTP client that would be mocked in small
tests and tested against real services in medium/large tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx


@dataclass
class User:
    """User model returned from the API."""

    id: int
    name: str
    email: str


@dataclass
class ApiError(Exception):
    """Exception raised when API calls fail."""

    status_code: int
    message: str


class ApiClient:
    """HTTP client for the user service API.

    This client is designed to be easily testable:
    - Small tests: Mock the HTTP client using pytest-httpx
    - Medium tests: Test against a local server on localhost
    - Large tests: Test against staging/production API
    """

    def __init__(self, base_url: str, client: httpx.Client | None = None) -> None:
        """Initialize the API client.

        Args:
            base_url: The base URL of the API (e.g., "https://api.example.com").
            client: Optional httpx client for dependency injection.

        """
        self.base_url = base_url.rstrip("/")
        self._client = client

    @property
    def client(self) -> httpx.Client:
        """Get the HTTP client, creating one if needed."""
        if self._client is None:
            import httpx

            self._client = httpx.Client()
        return self._client

    def get_user(self, user_id: int) -> User:
        """Fetch a user by ID.

        Args:
            user_id: The user's unique identifier.

        Returns:
            The User object.

        Raises:
            ApiError: If the API returns an error status code.

        """
        response = self.client.get(f"{self.base_url}/users/{user_id}")

        if response.status_code != 200:
            raise ApiError(
                status_code=response.status_code,
                message=f"Failed to fetch user {user_id}",
            )

        data = response.json()
        return User(id=data["id"], name=data["name"], email=data["email"])

    def create_user(self, name: str, email: str) -> User:
        """Create a new user.

        Args:
            name: The user's display name.
            email: The user's email address.

        Returns:
            The created User object with assigned ID.

        Raises:
            ApiError: If the API returns an error status code.

        """
        response = self.client.post(
            f"{self.base_url}/users",
            json={"name": name, "email": email},
        )

        if response.status_code not in (200, 201):
            raise ApiError(
                status_code=response.status_code,
                message=f"Failed to create user {name}",
            )

        data = response.json()
        return User(id=data["id"], name=data["name"], email=data["email"])

    def close(self) -> None:
        """Close the HTTP client connection."""
        if self._client is not None:
            self._client.close()
            self._client = None
