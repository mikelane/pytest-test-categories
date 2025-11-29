"""Production sleep blocker adapter using patching.

This module provides the production implementation of SleepBlockerPort that
actually intercepts sleep calls by patching time and asyncio modules.

The SleepPatchingBlocker follows hexagonal architecture principles:
- Implements the SleepBlockerPort interface (port)
- Patches sleep functions to intercept sleep attempts
- Raises SleepViolationError on unauthorized sleeps
- Restores original functions on deactivation

Intercepted Entry Points:
- time.sleep (standard library)
- asyncio.sleep (coroutine - returns immediately for small tests)

Note: threading.Event.wait() with timeout is not currently intercepted as it
has legitimate uses for synchronization. It can be added based on user feedback.

Example:
    >>> blocker = SleepPatchingBlocker()
    >>> try:
    ...     blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
    ...     time.sleep(0.1)  # Raises SleepViolationError
    ... finally:
    ...     blocker.deactivate()  # Restore original sleep behavior

See Also:
    - SleepBlockerPort: The abstract interface in ports/sleep.py
    - FakeSleepBlocker: Test adapter in adapters/fake_sleep.py
    - SubprocessPatchingBlocker: Similar production adapter pattern for process

"""

from __future__ import annotations

import asyncio
import time
from typing import (
    TYPE_CHECKING,
    Any,
)

from pydantic import Field

from pytest_test_categories.exceptions import SleepViolationError
from pytest_test_categories.ports.network import EnforcementMode
from pytest_test_categories.ports.sleep import SleepBlockerPort
from pytest_test_categories.types import TestSize

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine


class SleepPatchingBlocker(SleepBlockerPort):
    """Production adapter that patches time.sleep and asyncio.sleep to block sleep calls.

    This adapter intercepts sleep calls by patching:
    - time.sleep (standard library)
    - asyncio.sleep (coroutine)

    The patching is reversible - deactivate() restores the original functions.

    Attributes:
        state: Current blocker state (inherited from SleepBlockerPort).
        current_test_size: The test size set during activation.
        current_enforcement_mode: The enforcement mode set during activation.
        current_test_nodeid: The pytest node ID of the current test.

    Warning:
        This adapter modifies global state (time, asyncio modules). Always use
        in a try/finally block or context manager to ensure cleanup.

    Example:
        >>> blocker = SleepPatchingBlocker()
        >>> try:
        ...     blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        ...     time.sleep(0.1)  # Raises SleepViolationError
        ... finally:
        ...     blocker.deactivate()

    """

    current_test_size: TestSize | None = Field(default=None, description='Test size')
    current_enforcement_mode: EnforcementMode | None = Field(default=None, description='Enforcement mode')
    current_test_nodeid: str = Field(default='', description='Test node ID')

    def model_post_init(self, context: object, /) -> None:  # noqa: ARG002
        """Initialize post-Pydantic setup, storing references to original functions."""
        object.__setattr__(self, '_original_time_sleep', None)
        object.__setattr__(self, '_original_asyncio_sleep', None)

    def _do_activate(
        self,
        test_size: TestSize,
        enforcement_mode: EnforcementMode,
    ) -> None:
        """Install sleep wrappers to intercept sleep calls.

        Installs wrapper functions that intercept sleep attempts
        and check them against the test size restrictions.

        Args:
            test_size: The size category of the current test.
            enforcement_mode: How to handle violations.

        """
        self.current_test_size = test_size
        self.current_enforcement_mode = enforcement_mode

        # Store originals
        object.__setattr__(self, '_original_time_sleep', time.sleep)
        object.__setattr__(self, '_original_asyncio_sleep', asyncio.sleep)

        # Install patches
        time.sleep = self._create_patched_time_sleep()
        asyncio.sleep = self._create_patched_asyncio_sleep()  # type: ignore[assignment]

    def _do_deactivate(self) -> None:
        """Restore the original sleep functions.

        Restores all original functions that were saved during activation.

        """
        self._restore_originals()

    def _restore_originals(self) -> None:
        """Restore all original functions from stored references."""
        original_time_sleep = object.__getattribute__(self, '_original_time_sleep')
        if original_time_sleep is not None:
            time.sleep = original_time_sleep

        original_asyncio_sleep = object.__getattribute__(self, '_original_asyncio_sleep')
        if original_asyncio_sleep is not None:
            asyncio.sleep = original_asyncio_sleep

    def _do_check_sleep_allowed(self, function: str, duration: float) -> bool:  # noqa: ARG002
        """Check if sleep call is allowed by test size rules.

        Rules applied:
        - SMALL: Block all sleep calls
        - MEDIUM/LARGE/XLARGE: Allow all sleep calls

        Args:
            function: The sleep function name.
            duration: The sleep duration in seconds.

        Returns:
            True if the sleep is allowed, False if it should be blocked.

        """
        return self.current_test_size != TestSize.SMALL

    def _do_on_violation(
        self,
        function: str,
        duration: float,
        test_nodeid: str,
    ) -> None:
        """Handle a sleep violation based on enforcement mode.

        Behavior:
        - STRICT: Raise SleepViolationError
        - WARN: Log warning (future: integrate with pytest warning system)
        - OFF: Do nothing

        Args:
            function: The sleep function name.
            duration: The sleep duration in seconds.
            test_nodeid: The pytest node ID of the violating test.

        Raises:
            SleepViolationError: If enforcement mode is STRICT.

        """
        if self.current_enforcement_mode == EnforcementMode.STRICT:
            raise SleepViolationError(
                test_size=self.current_test_size,  # type: ignore[arg-type]
                test_nodeid=test_nodeid,
                function=function,
                duration=duration,
            )

    def reset(self) -> None:
        """Reset blocker to initial state, restoring original functions.

        This is safe to call regardless of current state.

        """
        self._restore_originals()

        # Clear stored references
        object.__setattr__(self, '_original_time_sleep', None)
        object.__setattr__(self, '_original_asyncio_sleep', None)

        super().reset()
        self.current_test_size = None
        self.current_enforcement_mode = None
        self.current_test_nodeid = ''

    def _create_patched_time_sleep(self) -> Callable[[float], None]:
        """Create a wrapper for time.sleep that intercepts sleep calls.

        Returns:
            A wrapper function that checks permissions before sleeping.

        """
        blocker = self
        original_sleep = object.__getattribute__(self, '_original_time_sleep')

        def patched_sleep(seconds: float) -> None:
            """Check sleep permissions before delegating to actual sleep.

            Args:
                seconds: The sleep duration in seconds.

            Raises:
                SleepViolationError: If sleep is not allowed
                    and enforcement mode is STRICT.

            """
            if not blocker._do_check_sleep_allowed('time.sleep', seconds):  # noqa: SLF001
                blocker._do_on_violation('time.sleep', seconds, blocker.current_test_nodeid)  # noqa: SLF001

            original_sleep(seconds)

        return patched_sleep

    def _create_patched_asyncio_sleep(self) -> Callable[[float], Coroutine[Any, Any, None]]:
        """Create a wrapper for asyncio.sleep that intercepts sleep calls.

        Returns:
            A wrapper coroutine function that checks permissions before sleeping.

        """
        blocker = self
        original_sleep = object.__getattribute__(self, '_original_asyncio_sleep')

        async def patched_sleep(delay: float) -> None:
            """Check sleep permissions before delegating to actual sleep.

            Args:
                delay: The sleep duration in seconds.

            Raises:
                SleepViolationError: If sleep is not allowed
                    and enforcement mode is STRICT.

            """
            if not blocker._do_check_sleep_allowed('asyncio.sleep', delay):  # noqa: SLF001
                blocker._do_on_violation('asyncio.sleep', delay, blocker.current_test_nodeid)  # noqa: SLF001

            await original_sleep(delay)

        return patched_sleep
