"""Integration tests for pytest-test-categories hexagonal architecture.

This package contains integration tests that verify:
1. Production adapters work with real external dependencies
2. Services work correctly with real adapters (not test doubles)
3. Full plugin orchestration through pytest infrastructure
4. End-to-end workflows from collection to reporting

All tests in this package are marked @pytest.mark.medium since they use
real infrastructure and are slower than unit tests.
"""

from __future__ import annotations
