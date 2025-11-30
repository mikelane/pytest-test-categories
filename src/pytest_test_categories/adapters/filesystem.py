"""Production filesystem blocker adapter using patching.

This module provides the production implementation of FilesystemBlockerPort that
actually intercepts filesystem operations by patching builtins.open, pathlib.Path,
os module functions, and shutil functions.

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
import os
import pathlib
import shutil
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


class _OriginalFunctions:
    """Container for storing original functions before patching."""

    def __init__(self) -> None:
        self.open: Callable[..., OpenReturnType] | None = None
        # pathlib.Path methods
        self.path_read_text: Callable[..., str] | None = None
        self.path_write_text: Callable[..., int] | None = None
        self.path_read_bytes: Callable[..., bytes] | None = None
        self.path_write_bytes: Callable[..., int] | None = None
        self.path_open: Callable[..., OpenReturnType] | None = None
        self.path_unlink: Callable[..., None] | None = None
        self.path_mkdir: Callable[..., None] | None = None
        self.path_rmdir: Callable[..., None] | None = None
        self.path_rename: Callable[..., Path] | None = None
        self.path_replace: Callable[..., Path] | None = None
        # os module functions
        self.os_remove: Callable[..., None] | None = None
        self.os_unlink: Callable[..., None] | None = None
        self.os_mkdir: Callable[..., None] | None = None
        self.os_makedirs: Callable[..., None] | None = None
        self.os_rmdir: Callable[..., None] | None = None
        self.os_rename: Callable[..., None] | None = None
        self.os_replace: Callable[..., None] | None = None
        # shutil functions
        self.shutil_copy: Callable[..., str] | None = None
        self.shutil_copy2: Callable[..., str] | None = None
        self.shutil_copytree: Callable[..., str] | None = None
        self.shutil_move: Callable[..., str] | None = None
        self.shutil_rmtree: Callable[..., None] | None = None


class FilesystemPatchingBlocker(FilesystemBlockerPort):
    """Production adapter that patches filesystem operations to block access.

    This adapter intercepts filesystem access by patching:
    - builtins.open
    - pathlib.Path methods (read_text, write_text, read_bytes, write_bytes, etc.)
    - os module functions (remove, mkdir, makedirs, etc.)
    - shutil functions (copy, move, rmtree, etc.)

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
        """Initialize post-Pydantic setup, storing reference to original functions."""
        object.__setattr__(self, '_originals', _OriginalFunctions())

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

        originals: _OriginalFunctions = object.__getattribute__(self, '_originals')

        # Store and patch builtins.open
        originals.open = builtins.open
        builtins.open = self._create_patched_open()  # type: ignore[assignment]

        # Store and patch pathlib.Path methods
        self._patch_pathlib_methods(originals)

        # Store and patch os module functions
        self._patch_os_functions(originals)

        # Store and patch shutil functions
        self._patch_shutil_functions(originals)

    def _do_deactivate(self) -> None:
        """Restore the original filesystem functions.

        Restores all patched functions to their original implementations.

        """
        self._restore_all_functions()

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
        self._restore_all_functions()

        super().reset()
        self.current_test_size = None
        self.current_enforcement_mode = None
        self.current_allowed_paths = frozenset()
        self.current_test_nodeid = ''

    def _restore_all_functions(self) -> None:
        """Restore all patched functions to their original implementations."""
        originals: _OriginalFunctions = object.__getattribute__(self, '_originals')

        # Restore builtins.open
        if originals.open is not None:
            builtins.open = originals.open  # type: ignore[assignment]
            originals.open = None

        # Restore pathlib.Path methods
        self._restore_pathlib_methods(originals)

        # Restore os module functions
        self._restore_os_functions(originals)

        # Restore shutil functions
        self._restore_shutil_functions(originals)

    def _patch_pathlib_methods(self, originals: _OriginalFunctions) -> None:
        """Patch pathlib.Path methods to intercept filesystem access."""
        # Store originals
        originals.path_read_text = pathlib.Path.read_text
        originals.path_write_text = pathlib.Path.write_text
        originals.path_read_bytes = pathlib.Path.read_bytes
        originals.path_write_bytes = pathlib.Path.write_bytes
        originals.path_open = pathlib.Path.open
        originals.path_unlink = pathlib.Path.unlink
        originals.path_mkdir = pathlib.Path.mkdir
        originals.path_rmdir = pathlib.Path.rmdir
        originals.path_rename = pathlib.Path.rename
        originals.path_replace = pathlib.Path.replace

        # Create patched versions
        pathlib.Path.read_text = self._create_patched_path_method(  # type: ignore[method-assign]
            originals.path_read_text, FilesystemOperation.READ
        )
        pathlib.Path.write_text = self._create_patched_path_method(  # type: ignore[method-assign]
            originals.path_write_text, FilesystemOperation.WRITE
        )
        pathlib.Path.read_bytes = self._create_patched_path_method(  # type: ignore[method-assign]
            originals.path_read_bytes, FilesystemOperation.READ
        )
        pathlib.Path.write_bytes = self._create_patched_path_method(  # type: ignore[method-assign]
            originals.path_write_bytes, FilesystemOperation.WRITE
        )
        pathlib.Path.open = self._create_patched_path_open(originals.path_open)  # type: ignore[method-assign,assignment]
        pathlib.Path.unlink = self._create_patched_path_method(  # type: ignore[method-assign]
            originals.path_unlink, FilesystemOperation.DELETE
        )
        pathlib.Path.mkdir = self._create_patched_path_method(  # type: ignore[method-assign]
            originals.path_mkdir, FilesystemOperation.CREATE
        )
        pathlib.Path.rmdir = self._create_patched_path_method(  # type: ignore[method-assign]
            originals.path_rmdir, FilesystemOperation.DELETE
        )
        pathlib.Path.rename = self._create_patched_path_method(  # type: ignore[method-assign]
            originals.path_rename, FilesystemOperation.MODIFY
        )
        pathlib.Path.replace = self._create_patched_path_method(  # type: ignore[method-assign]
            originals.path_replace, FilesystemOperation.MODIFY
        )

    def _restore_pathlib_methods(self, originals: _OriginalFunctions) -> None:
        """Restore pathlib.Path methods to their original implementations."""
        self._restore_pathlib_io_methods(originals)
        self._restore_pathlib_fs_methods(originals)

    def _restore_pathlib_io_methods(self, originals: _OriginalFunctions) -> None:
        """Restore pathlib.Path I/O methods (read/write/open)."""
        if originals.path_read_text is not None:
            pathlib.Path.read_text = originals.path_read_text  # type: ignore[method-assign]
            originals.path_read_text = None
        if originals.path_write_text is not None:
            pathlib.Path.write_text = originals.path_write_text  # type: ignore[method-assign]
            originals.path_write_text = None
        if originals.path_read_bytes is not None:
            pathlib.Path.read_bytes = originals.path_read_bytes  # type: ignore[method-assign]
            originals.path_read_bytes = None
        if originals.path_write_bytes is not None:
            pathlib.Path.write_bytes = originals.path_write_bytes  # type: ignore[method-assign]
            originals.path_write_bytes = None
        if originals.path_open is not None:
            pathlib.Path.open = originals.path_open  # type: ignore[method-assign,assignment]
            originals.path_open = None

    def _restore_pathlib_fs_methods(self, originals: _OriginalFunctions) -> None:
        """Restore pathlib.Path filesystem methods (unlink/mkdir/rmdir/rename/replace)."""
        if originals.path_unlink is not None:
            pathlib.Path.unlink = originals.path_unlink  # type: ignore[method-assign]
            originals.path_unlink = None
        if originals.path_mkdir is not None:
            pathlib.Path.mkdir = originals.path_mkdir  # type: ignore[method-assign]
            originals.path_mkdir = None
        if originals.path_rmdir is not None:
            pathlib.Path.rmdir = originals.path_rmdir  # type: ignore[method-assign]
            originals.path_rmdir = None
        if originals.path_rename is not None:
            pathlib.Path.rename = originals.path_rename  # type: ignore[method-assign,assignment]
            originals.path_rename = None
        if originals.path_replace is not None:
            pathlib.Path.replace = originals.path_replace  # type: ignore[method-assign,assignment]
            originals.path_replace = None

    def _patch_os_functions(self, originals: _OriginalFunctions) -> None:
        """Patch os module functions to intercept filesystem access."""
        # Store originals
        originals.os_remove = os.remove
        originals.os_unlink = os.unlink
        originals.os_mkdir = os.mkdir
        originals.os_makedirs = os.makedirs
        originals.os_rmdir = os.rmdir
        originals.os_rename = os.rename
        originals.os_replace = os.replace

        # Create patched versions
        os.remove = self._create_patched_os_function(originals.os_remove, FilesystemOperation.DELETE)
        os.unlink = self._create_patched_os_function(originals.os_unlink, FilesystemOperation.DELETE)
        os.mkdir = self._create_patched_os_function(originals.os_mkdir, FilesystemOperation.CREATE)
        os.makedirs = self._create_patched_os_function(originals.os_makedirs, FilesystemOperation.CREATE)
        os.rmdir = self._create_patched_os_function(originals.os_rmdir, FilesystemOperation.DELETE)
        os.rename = self._create_patched_os_rename(originals.os_rename)
        os.replace = self._create_patched_os_rename(originals.os_replace)

    def _restore_os_functions(self, originals: _OriginalFunctions) -> None:
        """Restore os module functions to their original implementations."""
        if originals.os_remove is not None:
            os.remove = originals.os_remove
            originals.os_remove = None
        if originals.os_unlink is not None:
            os.unlink = originals.os_unlink
            originals.os_unlink = None
        if originals.os_mkdir is not None:
            os.mkdir = originals.os_mkdir
            originals.os_mkdir = None
        if originals.os_makedirs is not None:
            os.makedirs = originals.os_makedirs
            originals.os_makedirs = None
        if originals.os_rmdir is not None:
            os.rmdir = originals.os_rmdir
            originals.os_rmdir = None
        if originals.os_rename is not None:
            os.rename = originals.os_rename
            originals.os_rename = None
        if originals.os_replace is not None:
            os.replace = originals.os_replace
            originals.os_replace = None

    def _patch_shutil_functions(self, originals: _OriginalFunctions) -> None:
        """Patch shutil functions to intercept filesystem access."""
        # Store originals
        originals.shutil_copy = shutil.copy
        originals.shutil_copy2 = shutil.copy2
        originals.shutil_copytree = shutil.copytree
        originals.shutil_move = shutil.move
        originals.shutil_rmtree = shutil.rmtree

        # Create patched versions
        shutil.copy = self._create_patched_shutil_copy(originals.shutil_copy)  # type: ignore[assignment]
        shutil.copy2 = self._create_patched_shutil_copy(originals.shutil_copy2)  # type: ignore[assignment]
        shutil.copytree = self._create_patched_shutil_copy(originals.shutil_copytree)  # type: ignore[assignment]
        shutil.move = self._create_patched_shutil_copy(originals.shutil_move)
        shutil.rmtree = self._create_patched_shutil_rmtree(originals.shutil_rmtree)  # type: ignore[assignment]

    def _restore_shutil_functions(self, originals: _OriginalFunctions) -> None:
        """Restore shutil functions to their original implementations."""
        if originals.shutil_copy is not None:
            shutil.copy = originals.shutil_copy  # type: ignore[assignment]
            originals.shutil_copy = None
        if originals.shutil_copy2 is not None:
            shutil.copy2 = originals.shutil_copy2  # type: ignore[assignment]
            originals.shutil_copy2 = None
        if originals.shutil_copytree is not None:
            shutil.copytree = originals.shutil_copytree  # type: ignore[assignment]
            originals.shutil_copytree = None
        if originals.shutil_move is not None:
            shutil.move = originals.shutil_move
            originals.shutil_move = None
        if originals.shutil_rmtree is not None:
            shutil.rmtree = originals.shutil_rmtree  # type: ignore[assignment]
            originals.shutil_rmtree = None

    def _create_patched_path_method(
        self,
        original: Callable[..., Any],
        operation: FilesystemOperation,
    ) -> Callable[..., Any]:
        """Create a patched pathlib.Path method.

        Args:
            original: The original unbound method.
            operation: The filesystem operation type.

        Returns:
            A wrapper function that checks permissions before delegating.

        """
        blocker = self

        def patched_method(self_path: Path, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            path = Path(self_path)
            if not blocker._do_check_access_allowed(path, operation):  # noqa: SLF001
                blocker.on_violation(path, operation, blocker.current_test_nodeid)
            return original(self_path, *args, **kwargs)

        return patched_method

    def _create_patched_path_open(
        self,
        original: Callable[..., OpenReturnType],
    ) -> Callable[..., OpenReturnType]:
        """Create a patched Path.open() method.

        Args:
            original: The original Path.open method.

        Returns:
            A wrapper that checks permissions before delegating.

        """
        blocker = self

        def patched_open(
            self_path: Path,
            mode: str = 'r',
            *args: Any,  # noqa: ANN401
            **kwargs: Any,  # noqa: ANN401
        ) -> OpenReturnType:
            path = Path(self_path)
            operation = blocker._determine_operation_from_mode(mode)  # noqa: SLF001
            if not blocker._do_check_access_allowed(path, operation):  # noqa: SLF001
                blocker.on_violation(path, operation, blocker.current_test_nodeid)
            return original(self_path, mode, *args, **kwargs)

        return patched_open

    def _create_patched_os_function(
        self,
        original: Callable[..., None],
        operation: FilesystemOperation,
    ) -> Callable[..., None]:
        """Create a patched os module function.

        Args:
            original: The original os module function.
            operation: The filesystem operation type.

        Returns:
            A wrapper that checks permissions before delegating.

        """
        blocker = self

        def patched_func(path: str | Path, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
            path_obj = Path(path) if isinstance(path, str) else path
            if not blocker._do_check_access_allowed(path_obj, operation):  # noqa: SLF001
                blocker.on_violation(path_obj, operation, blocker.current_test_nodeid)
            return original(path, *args, **kwargs)

        return patched_func

    def _create_patched_os_rename(
        self,
        original: Callable[..., None],
    ) -> Callable[..., None]:
        """Create a patched os.rename/replace function.

        Args:
            original: The original os.rename or os.replace function.

        Returns:
            A wrapper that checks permissions before delegating.

        """
        blocker = self

        def patched_rename(src: str | Path, dst: str | Path, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
            src_path = Path(src) if isinstance(src, str) else src
            if not blocker._do_check_access_allowed(src_path, FilesystemOperation.MODIFY):  # noqa: SLF001
                blocker.on_violation(src_path, FilesystemOperation.MODIFY, blocker.current_test_nodeid)
            return original(src, dst, *args, **kwargs)

        return patched_rename

    def _create_patched_shutil_copy(
        self,
        original: Callable[..., str],
    ) -> Callable[..., str]:
        """Create a patched shutil copy/move function.

        Args:
            original: The original shutil function.

        Returns:
            A wrapper that checks permissions before delegating.

        """
        blocker = self

        def patched_copy(src: str | Path, dst: str | Path, *args: Any, **kwargs: Any) -> str:  # noqa: ANN401
            src_path = Path(src) if isinstance(src, str) else src
            if not blocker._do_check_access_allowed(src_path, FilesystemOperation.READ):  # noqa: SLF001
                blocker.on_violation(src_path, FilesystemOperation.READ, blocker.current_test_nodeid)
            return original(src, dst, *args, **kwargs)

        return patched_copy

    def _create_patched_shutil_rmtree(
        self,
        original: Callable[..., None],
    ) -> Callable[..., None]:
        """Create a patched shutil.rmtree function.

        Args:
            original: The original shutil.rmtree function.

        Returns:
            A wrapper that checks permissions before delegating.

        """
        blocker = self

        def patched_rmtree(path: str | Path, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
            path_obj = Path(path) if isinstance(path, str) else path
            if not blocker._do_check_access_allowed(path_obj, FilesystemOperation.DELETE):  # noqa: SLF001
                blocker.on_violation(path_obj, FilesystemOperation.DELETE, blocker.current_test_nodeid)
            return original(path, *args, **kwargs)

        return patched_rmtree

    def _create_patched_open(self) -> Callable[..., OpenReturnType]:
        """Create a wrapper for builtins.open that intercepts file access.

        Returns:
            A wrapper function that checks permissions before delegating to real open.

        """
        blocker = self
        originals: _OriginalFunctions = object.__getattribute__(self, '_originals')
        original_open = originals.open
        if original_open is None:
            msg = 'original_open should be set during activation'
            raise RuntimeError(msg)

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
                blocker.on_violation(path, operation, blocker.current_test_nodeid)

            return original_open(file, mode, *args, **kwargs)

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
