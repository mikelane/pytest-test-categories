"""Test configuration and shared fixtures."""

from __future__ import annotations

pytest_plugins = [
    'pytester',
    'tests._fixtures.timer',
]
