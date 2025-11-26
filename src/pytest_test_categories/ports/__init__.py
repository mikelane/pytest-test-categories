"""Ports (interfaces) for hexagonal architecture.

This package contains abstract port definitions that define contracts
for resource isolation and enforcement. Implementations (adapters)
are provided in the `adapters` package.

Ports defined here:
- NetworkBlockerPort: Interface for network access control
"""

from __future__ import annotations

from pytest_test_categories.ports.network import NetworkBlockerPort

__all__ = [
    'NetworkBlockerPort',
]
