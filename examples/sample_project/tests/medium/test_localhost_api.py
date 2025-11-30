"""Tests using a local HTTP server.

These tests demonstrate medium-sized tests that use localhost
network access to test HTTP client behavior against a real server.

Note: These tests require network access to localhost, which is
allowed for medium tests but blocked for small tests.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING, ClassVar

import pytest

from sample_project.api_client import ApiClient, ApiError

if TYPE_CHECKING:
    from collections.abc import Generator


class MockUserApiHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler that simulates a user API."""

    users: ClassVar[dict[int, dict]] = {
        1: {"id": 1, "name": "Alice", "email": "alice@example.com"},
        2: {"id": 2, "name": "Bob", "email": "bob@example.com"},
    }
    next_id: ClassVar[int] = 3

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/users/"):
            user_id = int(self.path.split("/")[-1])
            if user_id in self.users:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(self.users[user_id]).encode())
            else:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/users":
            content_length = int(self.headers["Content-Length"])
            post_data = json.loads(self.rfile.read(content_length))
            new_user = {
                "id": MockUserApiHandler.next_id,
                "name": post_data["name"],
                "email": post_data["email"],
            }
            MockUserApiHandler.users[MockUserApiHandler.next_id] = new_user
            MockUserApiHandler.next_id += 1

            self.send_response(201)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(new_user).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        pass


@pytest.fixture
def local_api_server() -> Generator[str, None, None]:
    """Start a local HTTP server for testing.

    This fixture creates a real HTTP server on localhost that can
    be used to test HTTP client behavior in a controlled environment.

    Yields:
        The base URL of the local server (e.g., "http://127.0.0.1:8888").

    """
    # Reset state between tests
    MockUserApiHandler.users = {
        1: {"id": 1, "name": "Alice", "email": "alice@example.com"},
        2: {"id": 2, "name": "Bob", "email": "bob@example.com"},
    }
    MockUserApiHandler.next_id = 3

    server = HTTPServer(("127.0.0.1", 0), MockUserApiHandler)
    port = server.server_address[1]

    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    yield f"http://127.0.0.1:{port}"

    server.shutdown()


@pytest.mark.medium
class DescribeApiClientWithLocalServer:
    """Tests for ApiClient against a real local HTTP server.

    These tests verify HTTP client behavior with actual network I/O,
    catching issues that might be missed by mocked tests.
    """

    def it_fetches_existing_user(self, local_api_server: str) -> None:
        client = ApiClient(base_url=local_api_server)

        user = client.get_user(1)

        assert user.id == 1
        assert user.name == "Alice"
        client.close()

    def it_handles_missing_user(self, local_api_server: str) -> None:
        client = ApiClient(base_url=local_api_server)

        with pytest.raises(ApiError) as exc_info:
            client.get_user(999)

        assert exc_info.value.status_code == 404
        client.close()

    def it_creates_new_user(self, local_api_server: str) -> None:
        client = ApiClient(base_url=local_api_server)

        user = client.create_user(name="Charlie", email="charlie@example.com")

        assert user.id >= 3
        assert user.name == "Charlie"
        client.close()

    def it_retrieves_created_user(self, local_api_server: str) -> None:
        client = ApiClient(base_url=local_api_server)

        created = client.create_user(name="Dana", email="dana@example.com")
        retrieved = client.get_user(created.id)

        assert retrieved.name == "Dana"
        assert retrieved.email == "dana@example.com"
        client.close()
