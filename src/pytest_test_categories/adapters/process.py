"""Production process blocker adapter using patching.

This module provides the production implementation of ProcessBlockerPort that
actually intercepts process spawning by patching subprocess and os modules.

The SubprocessPatchingBlocker follows hexagonal architecture principles:
- Implements the ProcessBlockerPort interface (port)
- Patches subprocess and os functions to intercept spawn attempts
- Raises SubprocessViolationError on unauthorized spawns
- Restores original functions on deactivation

Intercepted Entry Points:
- subprocess.Popen (and all subprocess convenience functions)
- subprocess.run
- subprocess.call
- subprocess.check_call
- subprocess.check_output
- os.system
- os.popen
- multiprocessing.Process

Note: The os.spawn* and os.exec* families are not currently intercepted as they
are rarely used in modern Python code. They can be added based on user feedback.

Example:
    >>> blocker = SubprocessPatchingBlocker()
    >>> try:
    ...     blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
    ...     subprocess.run(['echo', 'hello'])  # Raises SubprocessViolationError
    ... finally:
    ...     blocker.deactivate()  # Restore original subprocess behavior

See Also:
    - ProcessBlockerPort: The abstract interface in ports/process.py
    - FakeProcessBlocker: Test adapter in adapters/fake_process.py
    - SocketPatchingNetworkBlocker: Similar production adapter pattern for network

"""

from __future__ import annotations

import multiprocessing
import os
import subprocess
from typing import (
    TYPE_CHECKING,
    Any,
)

from pydantic import Field

from pytest_test_categories.exceptions import SubprocessViolationError
from pytest_test_categories.ports.network import EnforcementMode
from pytest_test_categories.ports.process import ProcessBlockerPort
from pytest_test_categories.types import TestSize

if TYPE_CHECKING:
    from collections.abc import Callable


class SubprocessPatchingBlocker(ProcessBlockerPort):
    """Production adapter that patches subprocess/os to block process spawning.

    This adapter intercepts process spawning by patching:
    - subprocess.Popen (base class for all subprocess operations)
    - subprocess.run, call, check_call, check_output
    - os.system, os.popen
    - os.spawn* family
    - os.exec* family
    - multiprocessing.Process

    The patching is reversible - deactivate() restores the original functions.

    Attributes:
        state: Current blocker state (inherited from ProcessBlockerPort).
        current_test_size: The test size set during activation.
        current_enforcement_mode: The enforcement mode set during activation.
        current_test_nodeid: The pytest node ID of the current test.

    Warning:
        This adapter modifies global state (subprocess, os modules). Always use
        in a try/finally block or context manager to ensure cleanup.

    Example:
        >>> blocker = SubprocessPatchingBlocker()
        >>> try:
        ...     blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        ...     subprocess.run(['ls'])  # Raises SubprocessViolationError
        ... finally:
        ...     blocker.deactivate()

    """

    current_test_size: TestSize | None = Field(default=None, description='Test size')
    current_enforcement_mode: EnforcementMode | None = Field(default=None, description='Enforcement mode')
    current_test_nodeid: str = Field(default='', description='Test node ID')

    def model_post_init(self, context: object, /) -> None:  # noqa: ARG002
        """Initialize post-Pydantic setup, storing references to original functions."""
        object.__setattr__(self, '_original_popen', None)
        object.__setattr__(self, '_original_run', None)
        object.__setattr__(self, '_original_call', None)
        object.__setattr__(self, '_original_check_call', None)
        object.__setattr__(self, '_original_check_output', None)
        object.__setattr__(self, '_original_os_system', None)
        object.__setattr__(self, '_original_os_popen', None)
        object.__setattr__(self, '_original_mp_process', None)

    def _do_activate(self, test_size: TestSize, enforcement_mode: EnforcementMode) -> None:
        """Install subprocess/os wrappers to intercept process spawns.

        Installs wrapper functions that intercept process spawn attempts
        and check them against the test size restrictions.

        Args:
            test_size: The size category of the current test.
            enforcement_mode: How to handle violations.

        """
        self.current_test_size = test_size
        self.current_enforcement_mode = enforcement_mode

        # Store originals
        object.__setattr__(self, '_original_popen', subprocess.Popen)
        object.__setattr__(self, '_original_run', subprocess.run)
        object.__setattr__(self, '_original_call', subprocess.call)
        object.__setattr__(self, '_original_check_call', subprocess.check_call)
        object.__setattr__(self, '_original_check_output', subprocess.check_output)
        object.__setattr__(self, '_original_os_system', os.system)
        object.__setattr__(self, '_original_os_popen', os.popen)
        object.__setattr__(self, '_original_mp_process', multiprocessing.Process)

        # Install patches
        subprocess.Popen = self._create_patched_popen()  # type: ignore[misc,assignment]
        subprocess.run = self._create_patched_run()
        subprocess.call = self._create_patched_call()
        subprocess.check_call = self._create_patched_check_call()
        subprocess.check_output = self._create_patched_check_output()  # type: ignore[assignment]
        os.system = self._create_patched_os_system()  # type: ignore[assignment]
        os.popen = self._create_patched_os_popen()
        multiprocessing.Process = self._create_patched_mp_process()  # type: ignore[misc,assignment]

    def _do_deactivate(self) -> None:
        """Restore the original subprocess/os functions.

        Restores all the original functions that were saved during activation.

        """
        self._restore_originals()

    def _restore_originals(self) -> None:
        """Restore all original functions from stored references."""
        original_popen = object.__getattribute__(self, '_original_popen')
        if original_popen is not None:
            subprocess.Popen = original_popen  # type: ignore[misc]

        original_run = object.__getattribute__(self, '_original_run')
        if original_run is not None:
            subprocess.run = original_run

        original_call = object.__getattribute__(self, '_original_call')
        if original_call is not None:
            subprocess.call = original_call

        original_check_call = object.__getattribute__(self, '_original_check_call')
        if original_check_call is not None:
            subprocess.check_call = original_check_call

        original_check_output = object.__getattribute__(self, '_original_check_output')
        if original_check_output is not None:
            subprocess.check_output = original_check_output

        original_os_system = object.__getattribute__(self, '_original_os_system')
        if original_os_system is not None:
            os.system = original_os_system

        original_os_popen = object.__getattribute__(self, '_original_os_popen')
        if original_os_popen is not None:
            os.popen = original_os_popen

        original_mp_process = object.__getattribute__(self, '_original_mp_process')
        if original_mp_process is not None:
            multiprocessing.Process = original_mp_process  # type: ignore[misc]

    def _do_check_spawn_allowed(self, command: str, args: tuple[str, ...]) -> bool:  # noqa: ARG002
        """Check if process spawn is allowed by test size rules.

        Rules applied:
        - SMALL: Block all process spawning
        - MEDIUM/LARGE/XLARGE: Allow all process spawning

        Args:
            command: The command or executable to spawn.
            args: Arguments to pass to the command.

        Returns:
            True if the spawn is allowed, False if it should be blocked.

        """
        return self.current_test_size != TestSize.SMALL

    def _do_on_violation(
        self,
        command: str,
        args: tuple[str, ...],
        test_nodeid: str,
        method: str,
    ) -> None:
        """Handle a process spawn violation based on enforcement mode.

        Behavior:
        - STRICT: Raise SubprocessViolationError
        - WARN: Log warning (future: integrate with pytest warning system)
        - OFF: Do nothing

        Args:
            command: The attempted command.
            args: The attempted arguments.
            test_nodeid: The pytest node ID of the violating test.
            method: The spawn method used.

        Raises:
            SubprocessViolationError: If enforcement mode is STRICT.

        """
        if self.current_enforcement_mode == EnforcementMode.STRICT:
            raise SubprocessViolationError(
                test_size=self.current_test_size,  # type: ignore[arg-type]
                test_nodeid=test_nodeid,
                command=command,
                command_args=args,
                method=method,
            )

    def reset(self) -> None:
        """Reset blocker to initial state, restoring original functions.

        This is safe to call regardless of current state.

        """
        self._restore_originals()

        # Clear stored references
        object.__setattr__(self, '_original_popen', None)
        object.__setattr__(self, '_original_run', None)
        object.__setattr__(self, '_original_call', None)
        object.__setattr__(self, '_original_check_call', None)
        object.__setattr__(self, '_original_check_output', None)
        object.__setattr__(self, '_original_os_system', None)
        object.__setattr__(self, '_original_os_popen', None)
        object.__setattr__(self, '_original_mp_process', None)

        super().reset()
        self.current_test_size = None
        self.current_enforcement_mode = None
        self.current_test_nodeid = ''

    def _extract_command_and_args(self, args_input: Any) -> tuple[str, tuple[str, ...]]:  # noqa: ANN401
        """Extract command and args from various input formats.

        Args:
            args_input: The args parameter from subprocess calls (str, list, tuple).

        Returns:
            Tuple of (command, args).

        """
        if isinstance(args_input, str):
            return args_input, ()
        if isinstance(args_input, (list, tuple)) and args_input:
            return str(args_input[0]), tuple(str(a) for a in args_input[1:])
        return str(args_input), ()

    def _create_patched_popen(self) -> type:
        """Create a Popen wrapper that intercepts process spawns.

        Returns:
            A Popen subclass that checks permissions before spawning.

        """
        blocker = self
        original_popen = object.__getattribute__(self, '_original_popen')

        class BlockingPopen(original_popen):  # type: ignore[valid-type,misc]
            """Popen wrapper that enforces process blocking rules."""

            def __init__(
                self,
                args: Any,  # noqa: ANN401
                *pargs: Any,  # noqa: ANN401
                **kwargs: Any,  # noqa: ANN401
            ) -> None:
                """Check permissions then delegate to actual Popen."""
                command, cmd_args = blocker._extract_command_and_args(args)  # noqa: SLF001

                if not blocker._do_check_spawn_allowed(command, cmd_args):  # noqa: SLF001
                    blocker.on_violation(command, cmd_args, blocker.current_test_nodeid, 'subprocess.Popen')

                super().__init__(args, *pargs, **kwargs)

        return BlockingPopen

    def _create_patched_run(self) -> Callable[..., subprocess.CompletedProcess[Any]]:
        """Create a subprocess.run wrapper that intercepts process spawns.

        Returns:
            A wrapper function that checks permissions before running.

        """
        blocker = self
        original_run = object.__getattribute__(self, '_original_run')

        def patched_run(
            args: Any,  # noqa: ANN401
            *pargs: Any,  # noqa: ANN401
            **kwargs: Any,  # noqa: ANN401
        ) -> subprocess.CompletedProcess[Any]:
            """Check permissions then delegate to actual run."""
            command, cmd_args = blocker._extract_command_and_args(args)  # noqa: SLF001

            if not blocker._do_check_spawn_allowed(command, cmd_args):  # noqa: SLF001
                blocker.on_violation(command, cmd_args, blocker.current_test_nodeid, 'subprocess.run')

            return original_run(args, *pargs, **kwargs)  # type: ignore[no-any-return]

        return patched_run

    def _create_patched_call(self) -> Callable[..., int]:
        """Create a subprocess.call wrapper that intercepts process spawns.

        Returns:
            A wrapper function that checks permissions before calling.

        """
        blocker = self
        original_call = object.__getattribute__(self, '_original_call')

        def patched_call(
            args: Any,  # noqa: ANN401
            *pargs: Any,  # noqa: ANN401
            **kwargs: Any,  # noqa: ANN401
        ) -> int:
            """Check permissions then delegate to actual call."""
            command, cmd_args = blocker._extract_command_and_args(args)  # noqa: SLF001

            if not blocker._do_check_spawn_allowed(command, cmd_args):  # noqa: SLF001
                blocker.on_violation(command, cmd_args, blocker.current_test_nodeid, 'subprocess.call')

            return original_call(args, *pargs, **kwargs)  # type: ignore[no-any-return]

        return patched_call

    def _create_patched_check_call(self) -> Callable[..., int]:
        """Create a subprocess.check_call wrapper that intercepts process spawns.

        Returns:
            A wrapper function that checks permissions before calling.

        """
        blocker = self
        original_check_call = object.__getattribute__(self, '_original_check_call')

        def patched_check_call(
            args: Any,  # noqa: ANN401
            *pargs: Any,  # noqa: ANN401
            **kwargs: Any,  # noqa: ANN401
        ) -> int:
            """Check permissions then delegate to actual check_call."""
            command, cmd_args = blocker._extract_command_and_args(args)  # noqa: SLF001

            if not blocker._do_check_spawn_allowed(command, cmd_args):  # noqa: SLF001
                blocker.on_violation(command, cmd_args, blocker.current_test_nodeid, 'subprocess.check_call')

            return original_check_call(args, *pargs, **kwargs)  # type: ignore[no-any-return]

        return patched_check_call

    def _create_patched_check_output(self) -> Callable[..., bytes]:
        """Create a subprocess.check_output wrapper that intercepts process spawns.

        Returns:
            A wrapper function that checks permissions before calling.

        """
        blocker = self
        original_check_output = object.__getattribute__(self, '_original_check_output')

        def patched_check_output(
            args: Any,  # noqa: ANN401
            *pargs: Any,  # noqa: ANN401
            **kwargs: Any,  # noqa: ANN401
        ) -> bytes:
            """Check permissions then delegate to actual check_output."""
            command, cmd_args = blocker._extract_command_and_args(args)  # noqa: SLF001

            if not blocker._do_check_spawn_allowed(command, cmd_args):  # noqa: SLF001
                blocker.on_violation(command, cmd_args, blocker.current_test_nodeid, 'subprocess.check_output')

            return original_check_output(args, *pargs, **kwargs)  # type: ignore[no-any-return]

        return patched_check_output

    def _create_patched_os_system(self) -> Callable[[str], int]:
        """Create an os.system wrapper that intercepts process spawns.

        Returns:
            A wrapper function that checks permissions before calling.

        """
        blocker = self
        original_os_system = object.__getattribute__(self, '_original_os_system')

        def patched_os_system(command: str) -> int:
            """Check permissions then delegate to actual os.system."""
            if not blocker._do_check_spawn_allowed(command, ()):  # noqa: SLF001
                blocker.on_violation(command, (), blocker.current_test_nodeid, 'os.system')

            return original_os_system(command)  # type: ignore[no-any-return]

        return patched_os_system

    def _create_patched_os_popen(self) -> Callable[..., Any]:
        """Create an os.popen wrapper that intercepts process spawns.

        Returns:
            A wrapper function that checks permissions before calling.

        """
        blocker = self
        original_os_popen = object.__getattribute__(self, '_original_os_popen')

        def patched_os_popen(
            cmd: str,
            *pargs: Any,  # noqa: ANN401
            **kwargs: Any,  # noqa: ANN401
        ) -> Any:  # noqa: ANN401
            """Check permissions then delegate to actual os.popen."""
            if not blocker._do_check_spawn_allowed(cmd, ()):  # noqa: SLF001
                blocker.on_violation(cmd, (), blocker.current_test_nodeid, 'os.popen')

            return original_os_popen(cmd, *pargs, **kwargs)

        return patched_os_popen

    def _create_patched_mp_process(self) -> type:
        """Create a multiprocessing.Process wrapper that intercepts process spawns.

        Returns:
            A Process subclass that checks permissions before starting.

        """
        blocker = self
        original_mp_process = object.__getattribute__(self, '_original_mp_process')

        class BlockingProcess(original_mp_process):  # type: ignore[valid-type,misc]
            """Process wrapper that enforces process blocking rules."""

            def start(self) -> None:
                """Check permissions then delegate to actual start."""
                target = getattr(self, '_target', None) or getattr(self, 'target', None)
                target_name = getattr(target, '__name__', str(target)) if target else 'Process'

                if not blocker._do_check_spawn_allowed(target_name, ()):  # noqa: SLF001
                    blocker.on_violation(target_name, (), blocker.current_test_nodeid, 'multiprocessing.Process')

                super().start()

        return BlockingProcess
