"""Fake thread monitor adapter for testing.

This module provides a test double for the ThreadMonitorPort that allows
controllable simulation of thread monitoring without actual threading patching.
This enables fast, deterministic unit tests.

The FakeThreadMonitor follows hexagonal architecture principles:
- Implements the ThreadMonitorPort interface (port)
- Provides controllable behavior for testing
- Records thread creation attempts and method invocations
- No actual threading manipulation

Example:
    >>> monitor = FakeThreadMonitor()
    >>> monitor.activate(TestSize.SMALL, EnforcementMode.WARN)
    >>> monitor.on_thread_creation('threading.Thread', 'test::fn')
    >>> assert len(monitor.warnings) == 1

See Also:
    - ThreadMonitorPort: The abstract interface in ports/threading.py
    - ThreadPatchingMonitor: Production adapter in adapters/threading.py
    - FakeNetworkBlocker: Similar test double pattern for network blocking

"""

from __future__ import annotations

from pydantic import Field

from pytest_test_categories.ports.network import EnforcementMode
from pytest_test_categories.ports.threading import (
    ThreadCreationAttempt,
    ThreadMonitorPort,
)
from pytest_test_categories.types import TestSize


class FakeThreadMonitor(ThreadMonitorPort):
    """Test double for thread monitoring that records attempts without real patching.

    This adapter is designed for unit testing code that uses thread monitoring.
    It tracks all method calls and thread creation attempts for verification in tests.

    Attributes:
        state: Current monitor state (inherited from ThreadMonitorPort).
        current_test_size: The test size set during activation.
        current_enforcement_mode: The enforcement mode set during activation.
        thread_creation_attempts: List of recorded thread creation attempts.
        warnings: List of warning messages generated in WARN mode.
        activate_count: Number of times activate() was called.
        deactivate_count: Number of times deactivate() was called.
        thread_creation_count: Number of times on_thread_creation() was called.

    Example:
        >>> monitor = FakeThreadMonitor()
        >>> monitor.activate(TestSize.SMALL, EnforcementMode.WARN)
        >>> monitor.on_thread_creation('threading.Thread', 'test::fn')
        >>> assert len(monitor.warnings) == 1
        >>> assert monitor.thread_creation_count == 1

    """

    current_test_size: TestSize | None = Field(default=None, description='Test size')
    current_enforcement_mode: EnforcementMode | None = Field(default=None, description='Enforcement mode')
    thread_creation_attempts: list[ThreadCreationAttempt] = Field(default_factory=list, description='Attempts')
    warnings: list[str] = Field(default_factory=list, description='Warning messages')
    activate_count: int = Field(default=0, description='Count of activate() calls')
    deactivate_count: int = Field(default=0, description='Count of deactivate() calls')
    thread_creation_count: int = Field(default=0, description='Count of thread creation calls')

    @property
    def is_monitoring(self) -> bool:
        """Return True if actively monitoring for thread creation.

        Only small tests are monitored for threading usage.

        Returns:
            True if monitoring is active and test is SMALL, False otherwise.

        """
        return self.current_test_size == TestSize.SMALL

    def _do_activate(self, test_size: TestSize, enforcement_mode: EnforcementMode) -> None:
        """Record activation parameters for test verification.

        State transition is handled by the base class.

        Args:
            test_size: The size category of the current test.
            enforcement_mode: How to handle detections.

        """
        self.current_test_size = test_size
        self.current_enforcement_mode = enforcement_mode
        self.activate_count += 1

    def _do_deactivate(self) -> None:
        """Record deactivation for test verification.

        State transition is handled by the base class.

        """
        self.deactivate_count += 1

    def _do_on_thread_creation(self, thread_type: str, test_nodeid: str) -> None:
        """Record thread creation and generate warning if appropriate.

        For small tests with WARN mode, generates a warning message.

        Args:
            thread_type: The type of thread being created.
            test_nodeid: The pytest node ID of the test creating the thread.

        """
        self.thread_creation_count += 1

        self.thread_creation_attempts.append(
            ThreadCreationAttempt(
                thread_type=thread_type,
                test_nodeid=test_nodeid,
            )
        )

        if self.current_test_size == TestSize.SMALL and self.current_enforcement_mode == EnforcementMode.WARN:
            warning_msg = (
                f"Small test '{test_nodeid}' uses {thread_type}. "
                f'Small tests should be single-threaded for determinism. '
                f'Consider using @pytest.mark.medium if concurrency testing is required.'
            )
            self.warnings.append(warning_msg)

    def reset(self) -> None:
        """Reset monitor to initial state, clearing all recorded data.

        This is safe to call regardless of current state.

        """
        super().reset()
        self.current_test_size = None
        self.current_enforcement_mode = None
        self.thread_creation_attempts = []
        self.warnings = []
