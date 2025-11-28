"""Adapters for pytest integration following hexagonal architecture."""

from __future__ import annotations

from pytest_test_categories.adapters.fake_filesystem import FakeFilesystemBlocker
from pytest_test_categories.adapters.fake_network import FakeNetworkBlocker
from pytest_test_categories.adapters.fake_process import FakeProcessBlocker
from pytest_test_categories.adapters.filesystem import FilesystemPatchingBlocker
from pytest_test_categories.adapters.network import SocketPatchingNetworkBlocker
from pytest_test_categories.adapters.process import SubprocessPatchingBlocker
from pytest_test_categories.adapters.pytest_adapter import (
    PytestConfigAdapter,
    PytestItemAdapter,
    PytestWarningAdapter,
    TerminalReporterAdapter,
)

__all__ = [
    'FakeFilesystemBlocker',
    'FakeNetworkBlocker',
    'FakeProcessBlocker',
    'FilesystemPatchingBlocker',
    'PytestConfigAdapter',
    'PytestItemAdapter',
    'PytestWarningAdapter',
    'SocketPatchingNetworkBlocker',
    'SubprocessPatchingBlocker',
    'TerminalReporterAdapter',
]
