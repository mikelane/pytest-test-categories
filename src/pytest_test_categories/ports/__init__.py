"""Ports (interfaces) for hexagonal architecture.

This package contains abstract port definitions that define contracts
for resource isolation and enforcement. Implementations (adapters)
are provided in the `adapters` package.

Ports defined here:
- NetworkBlockerPort: Interface for network access control
- FilesystemBlockerPort: Interface for filesystem access control
- ProcessBlockerPort: Interface for subprocess/process spawn control
"""

from __future__ import annotations

from pytest_test_categories.ports.filesystem import (
    FilesystemAccessAttempt,
    FilesystemBlockerPort,
    FilesystemOperation,
)
from pytest_test_categories.ports.network import (
    BlockerState,
    ConnectionAttempt,
    EnforcementMode,
    NetworkBlockerPort,
)
from pytest_test_categories.ports.process import (
    ProcessBlockerPort,
    SpawnAttempt,
)

__all__ = [
    'BlockerState',
    'ConnectionAttempt',
    'EnforcementMode',
    'FilesystemAccessAttempt',
    'FilesystemBlockerPort',
    'FilesystemOperation',
    'NetworkBlockerPort',
    'ProcessBlockerPort',
    'SpawnAttempt',
]
