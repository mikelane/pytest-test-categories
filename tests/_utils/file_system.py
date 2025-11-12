"""File system port and adapters for testing infrastructure.

This module implements the hexagonal architecture pattern for file system operations:
- FileSystemPort: Abstract interface defining file system operations
- FakeFileSystem: In-memory test adapter for fast, deterministic testing
- RealFileSystem: Production adapter delegating to pathlib.Path

The port-adapter pattern enables:
- Unit tests to use FakeFileSystem (no disk I/O, fast, deterministic)
- Integration tests to use RealFileSystem (validates actual file operations)
- Easy testing of file system logic without implementation details
"""

from __future__ import annotations

from abc import (
    ABC,
    abstractmethod,
)
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from os import PathLike


class FileSystemPort(ABC):
    """Abstract interface for file system operations.

    This port defines the contract that all file system adapters must implement.
    It provides basic file operations needed for testing infrastructure.
    """

    @abstractmethod
    def exists(self, path: str | Path | PathLike) -> bool:
        """Check if a file exists.

        Args:
            path: File path to check.

        Returns:
            True if the file exists, False otherwise.

        """

    @abstractmethod
    def read_text(self, path: str | Path | PathLike) -> str:
        """Read the entire contents of a text file.

        Args:
            path: File path to read.

        Returns:
            The file contents as a string.

        Raises:
            FileNotFoundError: If the file does not exist.

        """

    @abstractmethod
    def write_text(self, path: str | Path | PathLike, content: str) -> None:
        """Write text content to a file, creating or overwriting as needed.

        Args:
            path: File path to write to.
            content: Text content to write.

        """


class FakeFileSystem(FileSystemPort):
    """In-memory file system adapter for testing.

    This test double stores files in memory rather than on disk, providing:
    - Fast, deterministic tests without I/O overhead
    - No cleanup required (no temporary files)
    - Complete control over file system state
    - Isolation between tests

    The FakeFileSystem follows hexagonal architecture principles:
    - Implements the FileSystemPort interface
    - Used in tests as a substitute for RealFileSystem
    - Enables testing behavior without implementation details

    Example:
        >>> fs = FakeFileSystem()
        >>> fs.write_text('/test/file.txt', 'content')
        >>> assert fs.exists('/test/file.txt')
        >>> assert fs.read_text('/test/file.txt') == 'content'

    """

    def __init__(self) -> None:
        """Initialize an empty in-memory file system."""
        self._files: dict[str, str] = {}

    def exists(self, path: str | Path | PathLike) -> bool:
        """Check if a file exists in the fake file system.

        Args:
            path: File path to check.

        Returns:
            True if the file exists in memory, False otherwise.

        """
        path_str = str(path)
        return path_str in self._files

    def read_text(self, path: str | Path | PathLike) -> str:
        """Read the contents of a file from memory.

        Args:
            path: File path to read.

        Returns:
            The file contents as a string.

        Raises:
            FileNotFoundError: If the file does not exist in memory.

        """
        path_str = str(path)
        if path_str not in self._files:
            msg = f'File not found: {path_str}'
            raise FileNotFoundError(msg)
        return self._files[path_str]

    def write_text(self, path: str | Path | PathLike, content: str) -> None:
        """Write text content to a file in memory.

        Args:
            path: File path to write to.
            content: Text content to store.

        """
        path_str = str(path)
        self._files[path_str] = content

    def set_file(self, path: str | Path | PathLike, content: str) -> None:
        """Set file content (alias for write_text).

        This provides a more test-friendly API for setting up test fixtures.

        Args:
            path: File path to set.
            content: Text content to store.

        """
        self.write_text(path, content)

    def get_file(self, path: str | Path | PathLike) -> str:
        """Get file content (alias for read_text).

        This provides a more test-friendly API for verifying test results.

        Args:
            path: File path to read.

        Returns:
            The file contents as a string.

        Raises:
            FileNotFoundError: If the file does not exist in memory.

        """
        return self.read_text(path)


class RealFileSystem(FileSystemPort):
    """Production file system adapter using pathlib.Path.

    This adapter delegates to Python's pathlib.Path for actual file I/O.
    It's used in production code and integration tests that need to verify
    real file system behavior.

    The RealFileSystem follows hexagonal architecture principles:
    - Implements the FileSystemPort interface
    - Delegates to pathlib.Path for actual file operations
    - Used in production and integration tests

    Example:
        >>> fs = RealFileSystem()
        >>> fs.write_text('/tmp/test.txt', 'content')
        >>> assert fs.exists('/tmp/test.txt')
        >>> assert fs.read_text('/tmp/test.txt') == 'content'

    """

    def exists(self, path: str | Path | PathLike) -> bool:
        """Check if a file exists on disk.

        Args:
            path: File path to check.

        Returns:
            True if the file exists on disk, False otherwise.

        """
        return Path(path).exists()

    def read_text(self, path: str | Path | PathLike) -> str:
        """Read the entire contents of a text file from disk.

        Args:
            path: File path to read.

        Returns:
            The file contents as a string.

        Raises:
            FileNotFoundError: If the file does not exist on disk.

        """
        return Path(path).read_text()

    def write_text(self, path: str | Path | PathLike, content: str) -> None:
        """Write text content to a file on disk.

        Args:
            path: File path to write to.
            content: Text content to write.

        """
        Path(path).write_text(content)
