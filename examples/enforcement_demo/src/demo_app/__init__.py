"""Demo application showcasing common external dependencies.

This package contains modules that demonstrate typical patterns that cause
test flakiness when not properly isolated:

- api_client: HTTP API client (network dependency)
- cache: TTL-based cache (time/sleep dependency)
- config: File-based configuration (filesystem dependency)
- shell: Shell command execution (subprocess dependency)
- worker: Background job processing (threading dependency)

Each module is designed to show both the "natural" implementation that
causes test problems and how to design for testability.
"""

from __future__ import annotations

from demo_app.api_client import ApiClient
from demo_app.cache import Cache
from demo_app.config import load_config
from demo_app.shell import ShellRunner
from demo_app.worker import BackgroundWorker

__all__ = [
    "ApiClient",
    "BackgroundWorker",
    "Cache",
    "ShellRunner",
    "load_config",
]
