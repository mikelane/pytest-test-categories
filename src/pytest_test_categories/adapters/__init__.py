"""Adapters for pytest integration following hexagonal architecture."""

from __future__ import annotations

from pytest_test_categories.adapters.fake_network import FakeNetworkBlocker
from pytest_test_categories.adapters.network import SocketPatchingNetworkBlocker
from pytest_test_categories.adapters.pytest_adapter import (
    PytestConfigAdapter,
    PytestItemAdapter,
    PytestWarningAdapter,
    TerminalReporterAdapter,
)

__all__ = [
    'FakeNetworkBlocker',
    'PytestConfigAdapter',
    'PytestItemAdapter',
    'PytestWarningAdapter',
    'SocketPatchingNetworkBlocker',
    'TerminalReporterAdapter',
]
