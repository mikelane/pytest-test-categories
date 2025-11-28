"""Fake filesystem blocker adapter for testing.

This module provides a test double for the FilesystemBlockerPort that allows
controllable simulation of filesystem blocking without actual patching.
This enables fast, deterministic unit tests.

The FakeFilesystemBlocker follows hexagonal architecture principles:
- Implements the FilesystemBlockerPort interface (port)
- Provides controllable behavior for testing
- Records access attempts and method invocations
- No actual filesystem patching

Example:
    >>> blocker = FakeFilesystemBlocker()
    >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())
    >>> blocker.check_access_allowed(Path('/etc/passwd'), FilesystemOperation.READ)
    False
    >>> assert len(blocker.access_attempts) == 1

See Also:
    - FilesystemBlockerPort: The abstract interface in ports/filesystem.py
    - FilesystemPatchingBlocker: Production adapter in adapters/filesystem.py
    - FakeNetworkBlocker: Similar test double pattern for network blocking

"""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 - Required at runtime for Pydantic and function signatures

from pydantic import Field

from pytest_test_categories.exceptions import FilesystemAccessViolationError
from pytest_test_categories.ports.filesystem import (
    FilesystemAccessAttempt,
    FilesystemBlockerPort,
    FilesystemOperation,
)
from pytest_test_categories.ports.network import EnforcementMode
from pytest_test_categories.types import TestSize


def is_path_under_allowed(path: Path, allowed_paths: frozenset[Path]) -> bool:
    """Check if a path is under any of the allowed paths.

    A path is considered "under" an allowed path if:
    - It is exactly equal to an allowed path
    - It is a child/descendant of an allowed path

    Args:
        path: The path to check (should be resolved/absolute).
        allowed_paths: Set of allowed base paths.

    Returns:
        True if the path is under any allowed path, False otherwise.

    Example:
        >>> allowed = frozenset([Path('/tmp')])
        >>> is_path_under_allowed(Path('/tmp/test.txt'), allowed)
        True
        >>> is_path_under_allowed(Path('/etc/passwd'), allowed)
        False

    """
    resolved_path = path.resolve()

    for allowed_path in allowed_paths:
        resolved_allowed = allowed_path.resolve()

        if resolved_path == resolved_allowed:
            return True

        try:
            resolved_path.relative_to(resolved_allowed)
        except ValueError:
            continue
        else:
            return True

    return False


class FakeFilesystemBlocker(FilesystemBlockerPort):
    """Test double for filesystem blocking that records attempts without real patching.

    This adapter is designed for unit testing code that uses filesystem blocking.
    It tracks all method calls and access attempts for verification in tests.

    Attributes:
        state: Current blocker state (inherited from FilesystemBlockerPort).
        current_test_size: The test size set during activation.
        current_enforcement_mode: The enforcement mode set during activation.
        current_allowed_paths: The allowed paths set during activation.
        access_attempts: List of recorded filesystem access attempts.
        warnings: List of warning messages generated in WARN mode.
        activate_count: Number of times activate() was called.
        deactivate_count: Number of times deactivate() was called.
        check_count: Number of times check_access_allowed() was called.

    Example:
        >>> blocker = FakeFilesystemBlocker()
        >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())
        >>> assert blocker.check_access_allowed(Path('/etc/passwd'), FilesystemOperation.READ) is False
        >>> assert blocker.check_count == 1

    """

    current_test_size: TestSize | None = Field(default=None, description='Test size')
    current_enforcement_mode: EnforcementMode | None = Field(default=None, description='Enforcement mode')
    current_allowed_paths: frozenset[Path] = Field(default_factory=frozenset, description='Allowed paths')
    access_attempts: list[FilesystemAccessAttempt] = Field(default_factory=list, description='Access attempts')
    warnings: list[str] = Field(default_factory=list, description='Warning messages')
    activate_count: int = Field(default=0, description='Count of activate() calls')
    deactivate_count: int = Field(default=0, description='Count of deactivate() calls')
    check_count: int = Field(default=0, description='Count of check calls')

    def _do_activate(
        self,
        test_size: TestSize,
        enforcement_mode: EnforcementMode,
        allowed_paths: frozenset[Path],
    ) -> None:
        """Record activation parameters for test verification.

        State transition is handled by the base class.

        Args:
            test_size: The size category of the current test.
            enforcement_mode: How to handle violations.
            allowed_paths: Paths that are always allowed.

        """
        self.current_test_size = test_size
        self.current_enforcement_mode = enforcement_mode
        self.current_allowed_paths = allowed_paths
        self.activate_count += 1

    def _do_deactivate(self) -> None:
        """Record deactivation for test verification.

        State transition is handled by the base class.

        """
        self.deactivate_count += 1

    def _do_check_access_allowed(self, path: Path, operation: FilesystemOperation) -> bool:
        """Check if filesystem access is allowed and record the attempt.

        Returns whether access would be allowed based on the test size:
        - SMALL: Block all filesystem access (except allowed paths)
        - MEDIUM/LARGE/XLARGE: Allow all filesystem access

        Args:
            path: The target path (resolved to absolute).
            operation: The type of filesystem operation.

        Returns:
            True if the access is allowed, False if it should be blocked.

        """
        self.check_count += 1

        allowed = self._is_access_allowed(path)

        self.access_attempts.append(
            FilesystemAccessAttempt(
                path=path,
                operation=operation,
                test_nodeid='',
                allowed=allowed,
            )
        )

        return allowed

    def _is_access_allowed(self, path: Path) -> bool:
        """Determine if filesystem access is allowed based on test size and allowed paths.

        Args:
            path: The target path.

        Returns:
            True if allowed, False otherwise.

        """
        if self.current_test_size == TestSize.SMALL:
            return is_path_under_allowed(path, self.current_allowed_paths)

        return True

    def _do_on_violation(
        self,
        path: Path,
        operation: FilesystemOperation,
        test_nodeid: str,
    ) -> None:
        """Handle a filesystem access violation based on enforcement mode.

        Behavior:
        - STRICT: Raise FilesystemAccessViolationError
        - WARN: Record warning message
        - OFF: Do nothing

        Args:
            path: The attempted path.
            operation: The attempted operation type.
            test_nodeid: The pytest node ID of the violating test.

        Raises:
            FilesystemAccessViolationError: If enforcement mode is STRICT.

        """
        if self.current_enforcement_mode == EnforcementMode.STRICT:
            raise FilesystemAccessViolationError(
                test_size=self.current_test_size,  # type: ignore[arg-type]
                test_nodeid=test_nodeid,
                path=path,
                operation=operation,
            )

        if self.current_enforcement_mode == EnforcementMode.WARN:
            warning_msg = f'Filesystem access violation: {operation.value} on {path} in test {test_nodeid}'
            self.warnings.append(warning_msg)

    def reset(self) -> None:
        """Reset blocker to initial state, clearing all recorded data.

        This is safe to call regardless of current state.

        """
        super().reset()
        self.current_test_size = None
        self.current_enforcement_mode = None
        self.current_allowed_paths = frozenset()
        self.access_attempts = []
        self.warnings = []
