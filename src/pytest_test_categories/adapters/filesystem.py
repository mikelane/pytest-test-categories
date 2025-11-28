"""Production filesystem blocker adapter using patching.

This module provides the production implementation of FilesystemBlockerPort that
actually intercepts filesystem operations by patching builtins.open, pathlib.Path,
and os module functions.

The FilesystemPatchingBlocker follows hexagonal architecture principles:
- Implements the FilesystemBlockerPort interface (port)
- Patches filesystem operations to intercept access attempts
- Raises FilesystemAccessViolationError on unauthorized access
- Restores original functions on deactivation

Example:
    >>> blocker = FilesystemPatchingBlocker()
    >>> try:
    ...     blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())
    ...     # Any open() call will now be intercepted
    ... finally:
    ...     blocker.deactivate()  # Restore original filesystem behavior

See Also:
    - FilesystemBlockerPort: The abstract interface in ports/filesystem.py
    - FakeFilesystemBlocker: Test adapter in adapters/fake_filesystem.py
    - SocketPatchingNetworkBlocker: Similar production adapter pattern for network

"""

from __future__ import annotations

import builtins
from io import (
    BufferedRandom,
    BufferedReader,
    BufferedWriter,
    FileIO,
    TextIOWrapper,
)
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
)

from pydantic import Field

from pytest_test_categories.adapters.fake_filesystem import is_path_under_allowed
from pytest_test_categories.exceptions import FilesystemAccessViolationError
from pytest_test_categories.ports.filesystem import (
    FilesystemBlockerPort,
    FilesystemOperation,
)
from pytest_test_categories.ports.network import EnforcementMode
from pytest_test_categories.types import TestSize

if TYPE_CHECKING:
    from collections.abc import Callable

OpenReturnType = TextIOWrapper | BufferedReader | BufferedWriter | BufferedRandom | FileIO


class FilesystemPatchingBlocker(FilesystemBlockerPort):
    """Production adapter that patches filesystem operations to block access.

    This adapter intercepts filesystem access by patching:
    - builtins.open
    - io.open (planned for extended operations)
    - pathlib.Path methods (planned for extended operations)
    - os module functions (planned for extended operations)

    The patching is reversible - deactivate() restores the original functions.

    Attributes:
        state: Current blocker state (inherited from FilesystemBlockerPort).
        current_test_size: The test size set during activation.
        current_enforcement_mode: The enforcement mode set during activation.
        current_allowed_paths: The allowed paths set during activation.
        current_test_nodeid: The pytest node ID of the current test.

    Warning:
        This adapter modifies global state (builtins.open). Always use in a
        try/finally block or context manager to ensure cleanup.

    Example:
        >>> blocker = FilesystemPatchingBlocker()
        >>> try:
        ...     blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())
        ...     open('/etc/passwd', 'r')  # Raises FilesystemAccessViolationError
        ... finally:
        ...     blocker.deactivate()

    """

    current_test_size: TestSize | None = Field(default=None, description='Test size')
    current_enforcement_mode: EnforcementMode | None = Field(default=None, description='Enforcement mode')
    current_allowed_paths: frozenset[Path] = Field(default_factory=frozenset, description='Allowed paths')
    current_test_nodeid: str = Field(default='', description='Test node ID')

    def model_post_init(self, context: object, /) -> None:  # noqa: ARG002
        """Initialize post-Pydantic setup, storing reference to original open."""
        object.__setattr__(self, '_original_open', None)

    def _do_activate(
        self,
        test_size: TestSize,
        enforcement_mode: EnforcementMode,
        allowed_paths: frozenset[Path],
    ) -> None:
        """Install filesystem wrappers to intercept operations.

        Installs wrapper functions that intercept filesystem operations
        and check them against the test size restrictions.

        Args:
            test_size: The size category of the current test.
            enforcement_mode: How to handle violations.
            allowed_paths: Paths that are always allowed.

        """
        self.current_test_size = test_size
        self.current_enforcement_mode = enforcement_mode
        self.current_allowed_paths = allowed_paths

        object.__setattr__(self, '_original_open', builtins.open)

        builtins.open = self._create_patched_open()  # type: ignore[assignment]

    def _do_deactivate(self) -> None:
        """Restore the original filesystem functions.

        Restores the original builtins.open that was saved during activation.

        """
        original = object.__getattribute__(self, '_original_open')
        if original is not None:
            builtins.open = original

    def _do_check_access_allowed(self, path: Path, operation: FilesystemOperation) -> bool:  # noqa: ARG002
        """Check if filesystem access to path is allowed by test size rules.

        Rules applied:
        - SMALL: Block all filesystem access (except allowed paths)
        - MEDIUM/LARGE/XLARGE: Allow all filesystem access

        Args:
            path: The target path (resolved to absolute).
            operation: The type of filesystem operation.

        Returns:
            True if the access is allowed, False if it should be blocked.

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
        - WARN: Log warning (future: integrate with pytest warning system)
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

    def reset(self) -> None:
        """Reset blocker to initial state, restoring original filesystem functions.

        This is safe to call regardless of current state.

        """
        original = object.__getattribute__(self, '_original_open')
        if original is not None:
            builtins.open = original
            object.__setattr__(self, '_original_open', None)

        super().reset()
        self.current_test_size = None
        self.current_enforcement_mode = None
        self.current_allowed_paths = frozenset()
        self.current_test_nodeid = ''

    def _create_patched_open(self) -> Callable[..., OpenReturnType]:
        """Create a wrapper for builtins.open that intercepts file access.

        Returns:
            A wrapper function that checks permissions before delegating to real open.

        """
        blocker = self
        original_open = object.__getattribute__(self, '_original_open')

        def patched_open(
            file: str | Path,
            mode: str = 'r',
            *args: Any,  # noqa: ANN401
            **kwargs: Any,  # noqa: ANN401
        ) -> OpenReturnType:
            """Check filesystem access permissions before opening file.

            Args:
                file: The file path to open.
                mode: The file mode (r, w, a, x, etc.).
                *args: Additional positional arguments for open().
                **kwargs: Additional keyword arguments for open().

            Returns:
                A file object if access is allowed.

            Raises:
                FilesystemAccessViolationError: If access is not allowed
                    and enforcement mode is STRICT.

            """
            path = Path(file) if isinstance(file, str) else file
            operation = blocker._determine_operation_from_mode(mode)  # noqa: SLF001

            if not blocker._do_check_access_allowed(path, operation):  # noqa: SLF001
                blocker._do_on_violation(path, operation, blocker.current_test_nodeid)  # noqa: SLF001

            return original_open(file, mode, *args, **kwargs)  # type: ignore[no-any-return]

        return patched_open

    @staticmethod
    def _determine_operation_from_mode(mode: str) -> FilesystemOperation:
        """Determine the filesystem operation type from open() mode.

        Args:
            mode: The file mode string (r, w, a, x, etc.).

        Returns:
            The corresponding FilesystemOperation.

        """
        if 'x' in mode:
            return FilesystemOperation.CREATE
        if 'w' in mode or 'a' in mode:
            return FilesystemOperation.WRITE
        return FilesystemOperation.READ
