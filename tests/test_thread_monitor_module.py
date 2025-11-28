"""Test the thread monitor adapters.

This module tests both the FakeThreadMonitor (test adapter) and
ThreadPatchingMonitor (production adapter) implementations.

The thread monitors follow hexagonal architecture:
- ThreadMonitorPort is the Port (interface)
- FakeThreadMonitor is a Test Adapter (test double)
- ThreadPatchingMonitor is a Production Adapter (real implementation)

This follows the same pattern as the network blocker module, but with
WARNINGS instead of ERRORS since threading is harder to completely block.
"""

from __future__ import annotations

import pytest
from icontract import ViolationError
from pydantic import ValidationError

from pytest_test_categories.adapters.fake_threading import FakeThreadMonitor
from pytest_test_categories.adapters.threading import ThreadPatchingMonitor
from pytest_test_categories.ports.network import (
    BlockerState,
    EnforcementMode,
)
from pytest_test_categories.ports.threading import (
    ThreadCreationAttempt,
)
from pytest_test_categories.types import TestSize


@pytest.mark.small
class DescribeFakeThreadMonitor:
    """Tests for the FakeThreadMonitor test double."""

    def it_starts_in_inactive_state(self) -> None:
        """Verify the monitor initializes in INACTIVE state."""
        monitor = FakeThreadMonitor()

        assert monitor.state == BlockerState.INACTIVE

    def it_transitions_to_active_on_activate(self) -> None:
        """Verify activate() transitions from INACTIVE to ACTIVE."""
        monitor = FakeThreadMonitor()

        monitor.activate(TestSize.SMALL, EnforcementMode.WARN)

        assert monitor.state == BlockerState.ACTIVE

    def it_transitions_to_inactive_on_deactivate(self) -> None:
        """Verify deactivate() transitions from ACTIVE to INACTIVE."""
        monitor = FakeThreadMonitor()
        monitor.activate(TestSize.SMALL, EnforcementMode.WARN)

        monitor.deactivate()

        assert monitor.state == BlockerState.INACTIVE

    def it_fails_to_activate_when_already_active(self) -> None:
        """Verify activate() raises when already ACTIVE."""
        monitor = FakeThreadMonitor()
        monitor.activate(TestSize.SMALL, EnforcementMode.WARN)

        with pytest.raises(ViolationError, match='INACTIVE'):
            monitor.activate(TestSize.SMALL, EnforcementMode.WARN)

    def it_fails_to_deactivate_when_inactive(self) -> None:
        """Verify deactivate() raises when already INACTIVE."""
        monitor = FakeThreadMonitor()

        with pytest.raises(ViolationError, match='ACTIVE'):
            monitor.deactivate()

    def it_records_activation_parameters(self) -> None:
        """Verify the monitor records test size and enforcement mode."""
        monitor = FakeThreadMonitor()

        monitor.activate(TestSize.SMALL, EnforcementMode.WARN)

        assert monitor.current_test_size == TestSize.SMALL
        assert monitor.current_enforcement_mode == EnforcementMode.WARN

    def it_monitors_small_tests(self) -> None:
        """Verify small tests are monitored for threading."""
        monitor = FakeThreadMonitor()

        monitor.activate(TestSize.SMALL, EnforcementMode.WARN)

        assert monitor.is_monitoring is True

    def it_does_not_monitor_medium_tests(self) -> None:
        """Verify medium tests are not monitored for threading."""
        monitor = FakeThreadMonitor()

        monitor.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        assert monitor.is_monitoring is False

    def it_does_not_monitor_large_tests(self) -> None:
        """Verify large tests are not monitored for threading."""
        monitor = FakeThreadMonitor()

        monitor.activate(TestSize.LARGE, EnforcementMode.WARN)

        assert monitor.is_monitoring is False

    def it_does_not_monitor_xlarge_tests(self) -> None:
        """Verify xlarge tests are not monitored for threading."""
        monitor = FakeThreadMonitor()

        monitor.activate(TestSize.XLARGE, EnforcementMode.WARN)

        assert monitor.is_monitoring is False

    def it_records_thread_creation_attempts(self) -> None:
        """Verify the monitor tracks thread creation attempts."""
        monitor = FakeThreadMonitor()
        monitor.activate(TestSize.SMALL, EnforcementMode.WARN)

        monitor.on_thread_creation('threading.Thread', 'test::fn')
        monitor.on_thread_creation('concurrent.futures.ThreadPoolExecutor', 'test::fn')

        assert len(monitor.thread_creation_attempts) == 2
        assert monitor.thread_creation_attempts[0] == ThreadCreationAttempt(
            thread_type='threading.Thread',
            test_nodeid='test::fn',
        )
        assert monitor.thread_creation_attempts[1] == ThreadCreationAttempt(
            thread_type='concurrent.futures.ThreadPoolExecutor',
            test_nodeid='test::fn',
        )

    def it_generates_warning_on_thread_creation_for_small_tests(self) -> None:
        """Verify warnings are generated for small tests using threading."""
        monitor = FakeThreadMonitor()
        monitor.activate(TestSize.SMALL, EnforcementMode.WARN)

        monitor.on_thread_creation('threading.Thread', 'test_module.py::test_fn')

        assert len(monitor.warnings) == 1
        assert 'threading.Thread' in monitor.warnings[0]
        assert 'test_module.py::test_fn' in monitor.warnings[0]
        assert 'Small' in monitor.warnings[0]

    def it_does_not_generate_warning_for_medium_tests(self) -> None:
        """Verify no warnings for medium tests using threading."""
        monitor = FakeThreadMonitor()
        monitor.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        monitor.on_thread_creation('threading.Thread', 'test_module.py::test_fn')

        assert len(monitor.warnings) == 0

    def it_does_not_generate_warning_for_large_tests(self) -> None:
        """Verify no warnings for large tests using threading."""
        monitor = FakeThreadMonitor()
        monitor.activate(TestSize.LARGE, EnforcementMode.WARN)

        monitor.on_thread_creation('threading.Thread', 'test_module.py::test_fn')

        assert len(monitor.warnings) == 0

    def it_does_not_generate_warning_for_xlarge_tests(self) -> None:
        """Verify no warnings for xlarge tests using threading."""
        monitor = FakeThreadMonitor()
        monitor.activate(TestSize.XLARGE, EnforcementMode.WARN)

        monitor.on_thread_creation('threading.Thread', 'test_module.py::test_fn')

        assert len(monitor.warnings) == 0

    def it_does_nothing_in_off_mode(self) -> None:
        """Verify no warnings in OFF mode even for small tests."""
        monitor = FakeThreadMonitor()
        monitor.activate(TestSize.SMALL, EnforcementMode.OFF)

        monitor.on_thread_creation('threading.Thread', 'test_module.py::test_fn')

        assert len(monitor.warnings) == 0

    def it_fails_on_thread_creation_when_inactive(self) -> None:
        """Verify on_thread_creation raises when INACTIVE."""
        monitor = FakeThreadMonitor()

        with pytest.raises(ViolationError, match='ACTIVE'):
            monitor.on_thread_creation('threading.Thread', 'test::fn')

    def it_resets_to_initial_state(self) -> None:
        """Verify reset() returns monitor to initial state."""
        monitor = FakeThreadMonitor()
        monitor.activate(TestSize.SMALL, EnforcementMode.WARN)
        monitor.on_thread_creation('threading.Thread', 'test::fn')

        monitor.reset()

        assert monitor.state == BlockerState.INACTIVE
        assert monitor.current_test_size is None
        assert monitor.current_enforcement_mode is None
        assert len(monitor.thread_creation_attempts) == 0
        assert len(monitor.warnings) == 0

    def it_resets_even_when_active(self) -> None:
        """Verify reset() works regardless of current state."""
        monitor = FakeThreadMonitor()
        monitor.activate(TestSize.SMALL, EnforcementMode.WARN)

        monitor.reset()

        assert monitor.state == BlockerState.INACTIVE

    def it_tracks_call_counts(self) -> None:
        """Verify the monitor tracks method invocation counts."""
        monitor = FakeThreadMonitor()

        monitor.activate(TestSize.SMALL, EnforcementMode.WARN)
        monitor.on_thread_creation('threading.Thread', 'test::fn')
        monitor.on_thread_creation('threading.Timer', 'test::fn')
        monitor.deactivate()

        assert monitor.activate_count == 1
        assert monitor.deactivate_count == 1
        assert monitor.thread_creation_count == 2


@pytest.mark.small
class DescribeThreadPatchingMonitor:
    """Tests for the ThreadPatchingMonitor production adapter."""

    def it_starts_in_inactive_state(self) -> None:
        """Verify the monitor initializes in INACTIVE state."""
        monitor = ThreadPatchingMonitor()

        assert monitor.state == BlockerState.INACTIVE

    def it_transitions_to_active_on_activate(self) -> None:
        """Verify activate() transitions from INACTIVE to ACTIVE."""
        monitor = ThreadPatchingMonitor()

        monitor.activate(TestSize.SMALL, EnforcementMode.WARN)

        assert monitor.state == BlockerState.ACTIVE

        monitor.deactivate()

    def it_transitions_to_inactive_on_deactivate(self) -> None:
        """Verify deactivate() transitions from ACTIVE to INACTIVE."""
        monitor = ThreadPatchingMonitor()
        monitor.activate(TestSize.SMALL, EnforcementMode.WARN)

        monitor.deactivate()

        assert monitor.state == BlockerState.INACTIVE

    def it_fails_to_activate_when_already_active(self) -> None:
        """Verify activate() raises when already ACTIVE."""
        monitor = ThreadPatchingMonitor()
        monitor.activate(TestSize.SMALL, EnforcementMode.WARN)

        try:
            with pytest.raises(ViolationError, match='INACTIVE'):
                monitor.activate(TestSize.SMALL, EnforcementMode.WARN)
        finally:
            monitor.reset()

    def it_fails_to_deactivate_when_inactive(self) -> None:
        """Verify deactivate() raises when already INACTIVE."""
        monitor = ThreadPatchingMonitor()

        with pytest.raises(ViolationError, match='ACTIVE'):
            monitor.deactivate()

    def it_stores_activation_parameters(self) -> None:
        """Verify the monitor stores test size and enforcement mode."""
        monitor = ThreadPatchingMonitor()

        monitor.activate(TestSize.SMALL, EnforcementMode.WARN)

        assert monitor.current_test_size == TestSize.SMALL
        assert monitor.current_enforcement_mode == EnforcementMode.WARN

        monitor.deactivate()

    def it_monitors_small_tests(self) -> None:
        """Verify small tests are monitored for threading."""
        monitor = ThreadPatchingMonitor()

        monitor.activate(TestSize.SMALL, EnforcementMode.WARN)

        assert monitor.is_monitoring is True

        monitor.deactivate()

    def it_does_not_monitor_medium_tests(self) -> None:
        """Verify medium tests are not monitored for threading."""
        monitor = ThreadPatchingMonitor()

        monitor.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        assert monitor.is_monitoring is False

        monitor.deactivate()

    def it_resets_to_initial_state(self) -> None:
        """Verify reset() returns monitor to initial state."""
        monitor = ThreadPatchingMonitor()
        monitor.activate(TestSize.SMALL, EnforcementMode.WARN)

        monitor.reset()

        assert monitor.state == BlockerState.INACTIVE
        assert monitor.current_test_size is None
        assert monitor.current_enforcement_mode is None

    def it_patches_threading_module_on_activate(self) -> None:
        """Verify threading.Thread is patched when activated."""
        import threading

        original_thread = threading.Thread
        monitor = ThreadPatchingMonitor()

        monitor.activate(TestSize.SMALL, EnforcementMode.WARN)

        assert threading.Thread is not original_thread

        monitor.deactivate()

        assert threading.Thread is original_thread

    def it_restores_threading_module_on_deactivate(self) -> None:
        """Verify threading.Thread is restored when deactivated."""
        import threading

        original_thread = threading.Thread
        monitor = ThreadPatchingMonitor()

        monitor.activate(TestSize.SMALL, EnforcementMode.WARN)
        monitor.deactivate()

        assert threading.Thread is original_thread

    def it_restores_threading_module_on_reset(self) -> None:
        """Verify threading.Thread is restored on reset."""
        import threading

        original_thread = threading.Thread
        monitor = ThreadPatchingMonitor()

        monitor.activate(TestSize.SMALL, EnforcementMode.WARN)
        monitor.reset()

        assert threading.Thread is original_thread

    def it_patches_concurrent_futures_thread_pool_executor(self) -> None:
        """Verify ThreadPoolExecutor is patched when activated."""
        import concurrent.futures

        original_executor = concurrent.futures.ThreadPoolExecutor
        monitor = ThreadPatchingMonitor()

        monitor.activate(TestSize.SMALL, EnforcementMode.WARN)

        patched_executor = concurrent.futures.ThreadPoolExecutor

        assert patched_executor is not original_executor

        monitor.deactivate()


@pytest.mark.small
class DescribeThreadCreationAttempt:
    """Tests for the ThreadCreationAttempt model."""

    def it_creates_immutable_record(self) -> None:
        """Verify ThreadCreationAttempt is immutable."""
        attempt = ThreadCreationAttempt(
            thread_type='threading.Thread',
            test_nodeid='test_module.py::test_fn',
        )

        with pytest.raises(ValidationError, match='frozen'):
            attempt.thread_type = 'modified'  # type: ignore[misc]

    def it_stores_thread_type_and_nodeid(self) -> None:
        """Verify ThreadCreationAttempt stores required fields."""
        attempt = ThreadCreationAttempt(
            thread_type='concurrent.futures.ThreadPoolExecutor',
            test_nodeid='tests/test_concurrent.py::test_parallel',
        )

        assert attempt.thread_type == 'concurrent.futures.ThreadPoolExecutor'
        assert attempt.test_nodeid == 'tests/test_concurrent.py::test_parallel'
