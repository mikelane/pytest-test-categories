"""Shell command execution demonstrating subprocess dependency patterns.

This module shows shell command execution. Tests for subprocess calls
often become flaky because they:
- Depend on external tools being installed
- Have different behavior on different systems
- Can fail due to environment differences
- Are slow compared to pure Python tests

Solutions:
1. Mock subprocess.run/Popen using pytest-mock
2. Use dependency injection for the executor
3. Test command-building logic separately from execution
4. Use medium tests for actual subprocess integration
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Protocol,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass
class CommandResult:
    """Result of a shell command execution."""

    return_code: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        """Check if the command succeeded."""
        return self.return_code == 0


class CommandExecutor(Protocol):
    """Protocol for command execution - enables dependency injection."""

    def execute(self, args: Sequence[str]) -> CommandResult: ...


class RealCommandExecutor:
    """Real subprocess executor - the default implementation."""

    def execute(self, args: Sequence[str]) -> CommandResult:
        """Execute a command using subprocess.

        Args:
            args: Command and arguments.

        Returns:
            CommandResult with output and return code.

        """
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False,
        )
        return CommandResult(
            return_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )


class FakeCommandExecutor:
    """Fake executor for testing - no actual subprocess spawning."""

    def __init__(self) -> None:
        """Initialize with empty response queue."""
        self._responses: dict[tuple[str, ...], CommandResult] = {}
        self._default_response = CommandResult(return_code=0, stdout="", stderr="")
        self.executed_commands: list[tuple[str, ...]] = []

    def add_response(
        self,
        args: Sequence[str],
        return_code: int = 0,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        """Add a canned response for a command.

        Args:
            args: Command and arguments to match.
            return_code: Return code to return.
            stdout: Stdout to return.
            stderr: Stderr to return.

        """
        self._responses[tuple(args)] = CommandResult(
            return_code=return_code,
            stdout=stdout,
            stderr=stderr,
        )

    def execute(self, args: Sequence[str]) -> CommandResult:
        """Return canned response without executing.

        Args:
            args: Command and arguments.

        Returns:
            Canned CommandResult.

        """
        self.executed_commands.append(tuple(args))
        return self._responses.get(tuple(args), self._default_response)


@dataclass
class ShellRunner:
    """Shell command runner with injectable executor.

    This design allows testing command-building logic without
    actually spawning processes.
    """

    _executor: CommandExecutor | None = None

    def __post_init__(self) -> None:
        """Set default executor if not provided."""
        if self._executor is None:
            self._executor = RealCommandExecutor()

    @property
    def executor(self) -> CommandExecutor:
        """Get the executor, guaranteed to be set after init."""
        assert self._executor is not None  # Guaranteed by __post_init__
        return self._executor

    def run(self, command: str, *args: str) -> CommandResult:
        """Run a shell command.

        Args:
            command: The command to run.
            *args: Additional arguments.

        Returns:
            CommandResult with output and return code.

        """
        full_args = [command, *args]
        return self.executor.execute(full_args)

    def git_version(self) -> str:
        """Get the git version.

        Returns:
            Git version string, or 'unknown' if git is not available.

        """
        result = self.run("git", "--version")
        if result.success:
            return result.stdout.strip()
        return "unknown"

    def list_directory(self, path: str = ".") -> list[str]:
        """List directory contents.

        Args:
            path: Directory path to list.

        Returns:
            List of file/directory names.

        """
        result = self.run("ls", "-1", path)
        if result.success:
            return result.stdout.strip().split("\n")
        return []

    def disk_usage(self, path: str = ".") -> str:
        """Get disk usage for a path.

        Args:
            path: Path to check.

        Returns:
            Disk usage string from du command.

        """
        result = self.run("du", "-sh", path)
        if result.success:
            return result.stdout.strip()
        return "unknown"
