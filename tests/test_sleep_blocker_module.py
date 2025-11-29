"""Test the sleep blocker adapters.

This module tests both the FakeSleepBlocker (test adapter) and
SleepPatchingBlocker (production adapter) implementations.

The sleep blockers follow hexagonal architecture:
- SleepBlockerPort is the Port (interface)
- FakeSleepBlocker is a Test Adapter (test double)
- SleepPatchingBlocker is a Production Adapter (real implementation)

This follows the same pattern as the network, filesystem, process, and database
blocker modules.

Sleep isolation ensures small tests remain hermetic by blocking:
- time.sleep (standard library)
- asyncio.sleep (coroutine)

Small tests should not depend on wall-clock time. Sleep calls indicate:
- Waiting for async operations (should use proper synchronization)
- Flaky timing assumptions
- Polling patterns (should use condition-based waiting)
"""

from __future__ import annotations

import pytest
from icontract import ViolationError

from pytest_test_categories.adapters.fake_sleep import FakeSleepBlocker
from pytest_test_categories.adapters.sleep import SleepPatchingBlocker
from pytest_test_categories.exceptions import SleepViolationError
from pytest_test_categories.ports.network import (
    BlockerState,
    EnforcementMode,
)
from pytest_test_categories.ports.sleep import SleepAttempt
from pytest_test_categories.types import TestSize


@pytest.mark.small
class DescribeFakeSleepBlocker:
    """Tests for the FakeSleepBlocker test double."""

    def it_starts_in_inactive_state(self) -> None:
        """Verify the blocker initializes in INACTIVE state."""
        blocker = FakeSleepBlocker()

        assert blocker.state == BlockerState.INACTIVE

    def it_transitions_to_active_on_activate(self) -> None:
        """Verify activate() transitions from INACTIVE to ACTIVE."""
        blocker = FakeSleepBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        assert blocker.state == BlockerState.ACTIVE

    def it_transitions_to_inactive_on_deactivate(self) -> None:
        """Verify deactivate() transitions from ACTIVE to INACTIVE."""
        blocker = FakeSleepBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        blocker.deactivate()

        assert blocker.state == BlockerState.INACTIVE

    def it_fails_to_activate_when_already_active(self) -> None:
        """Verify activate() raises when already ACTIVE."""
        blocker = FakeSleepBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        with pytest.raises(ViolationError, match='INACTIVE'):
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

    def it_fails_to_deactivate_when_inactive(self) -> None:
        """Verify deactivate() raises when already INACTIVE."""
        blocker = FakeSleepBlocker()

        with pytest.raises(ViolationError, match='ACTIVE'):
            blocker.deactivate()

    def it_records_activation_parameters(self) -> None:
        """Verify the blocker records test size and enforcement mode."""
        blocker = FakeSleepBlocker()

        blocker.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        assert blocker.current_test_size == TestSize.MEDIUM
        assert blocker.current_enforcement_mode == EnforcementMode.WARN

    def it_blocks_all_sleep_calls_for_small_tests(self) -> None:
        """Verify small tests cannot use any sleep function."""
        blocker = FakeSleepBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        assert blocker.check_sleep_allowed('time.sleep', 0.1) is False
        assert blocker.check_sleep_allowed('time.sleep', 1.0) is False
        assert blocker.check_sleep_allowed('asyncio.sleep', 0.5) is False

    def it_allows_all_sleep_calls_for_medium_tests(self) -> None:
        """Verify medium tests can use any sleep function."""
        blocker = FakeSleepBlocker()
        blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)

        assert blocker.check_sleep_allowed('time.sleep', 0.1) is True
        assert blocker.check_sleep_allowed('asyncio.sleep', 1.0) is True

    def it_allows_all_sleep_calls_for_large_tests(self) -> None:
        """Verify large tests can use any sleep function."""
        blocker = FakeSleepBlocker()
        blocker.activate(TestSize.LARGE, EnforcementMode.STRICT)

        assert blocker.check_sleep_allowed('time.sleep', 0.1) is True
        assert blocker.check_sleep_allowed('asyncio.sleep', 5.0) is True

    def it_allows_all_sleep_calls_for_xlarge_tests(self) -> None:
        """Verify xlarge tests can use any sleep function."""
        blocker = FakeSleepBlocker()
        blocker.activate(TestSize.XLARGE, EnforcementMode.STRICT)

        assert blocker.check_sleep_allowed('time.sleep', 10.0) is True
        assert blocker.check_sleep_allowed('asyncio.sleep', 60.0) is True

    def it_records_sleep_attempts(self) -> None:
        """Verify the blocker tracks sleep call attempts."""
        blocker = FakeSleepBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        blocker.check_sleep_allowed('time.sleep', 0.1)
        blocker.check_sleep_allowed('asyncio.sleep', 0.5)

        assert len(blocker.sleep_attempts) == 2
        assert blocker.sleep_attempts[0] == SleepAttempt(
            function='time.sleep',
            duration=0.1,
            test_nodeid='',
            allowed=False,
        )
        assert blocker.sleep_attempts[1] == SleepAttempt(
            function='asyncio.sleep',
            duration=0.5,
            test_nodeid='',
            allowed=False,
        )

    def it_raises_on_violation_in_strict_mode(self) -> None:
        """Verify on_violation raises SleepViolationError in STRICT mode."""
        blocker = FakeSleepBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        with pytest.raises(SleepViolationError) as exc_info:
            blocker.on_violation('time.sleep', 0.1, 'test_module.py::test_fn')

        assert exc_info.value.function == 'time.sleep'
        assert exc_info.value.duration == 0.1
        assert exc_info.value.test_size == TestSize.SMALL

    def it_records_warning_in_warn_mode(self) -> None:
        """Verify on_violation records warning in WARN mode."""
        blocker = FakeSleepBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.WARN)

        blocker.on_violation('time.sleep', 0.5, 'test_module.py::test_fn')

        assert len(blocker.warnings) == 1
        assert 'time.sleep' in blocker.warnings[0]
        assert '0.5' in blocker.warnings[0]

    def it_does_nothing_in_off_mode(self) -> None:
        """Verify on_violation does nothing in OFF mode."""
        blocker = FakeSleepBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.OFF)

        blocker.on_violation('time.sleep', 0.1, 'test_module.py::test_fn')

        assert len(blocker.warnings) == 0

    def it_fails_check_sleep_when_inactive(self) -> None:
        """Verify check_sleep_allowed raises when INACTIVE."""
        blocker = FakeSleepBlocker()

        with pytest.raises(ViolationError, match='ACTIVE'):
            blocker.check_sleep_allowed('time.sleep', 0.1)

    def it_fails_on_violation_when_inactive(self) -> None:
        """Verify on_violation raises when INACTIVE."""
        blocker = FakeSleepBlocker()

        with pytest.raises(ViolationError, match='ACTIVE'):
            blocker.on_violation('time.sleep', 0.1, 'test::fn')

    def it_resets_to_initial_state(self) -> None:
        """Verify reset() returns blocker to initial state."""
        blocker = FakeSleepBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        blocker.check_sleep_allowed('time.sleep', 0.1)

        blocker.reset()

        assert blocker.state == BlockerState.INACTIVE
        assert blocker.current_test_size is None
        assert blocker.current_enforcement_mode is None
        assert len(blocker.sleep_attempts) == 0
        assert len(blocker.warnings) == 0

    def it_resets_even_when_active(self) -> None:
        """Verify reset() works regardless of current state."""
        blocker = FakeSleepBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        blocker.reset()

        assert blocker.state == BlockerState.INACTIVE

    def it_tracks_call_counts(self) -> None:
        """Verify the blocker tracks method invocation counts."""
        blocker = FakeSleepBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        blocker.check_sleep_allowed('time.sleep', 0.1)
        blocker.check_sleep_allowed('asyncio.sleep', 0.2)
        blocker.deactivate()

        assert blocker.activate_count == 1
        assert blocker.deactivate_count == 1
        assert blocker.check_count == 2


@pytest.mark.small
class DescribeSleepPatchingBlocker:
    """Tests for the SleepPatchingBlocker production adapter."""

    def it_starts_in_inactive_state(self) -> None:
        """Verify the blocker initializes in INACTIVE state."""
        blocker = SleepPatchingBlocker()

        assert blocker.state == BlockerState.INACTIVE

    def it_transitions_to_active_on_activate(self) -> None:
        """Verify activate() transitions from INACTIVE to ACTIVE."""
        blocker = SleepPatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        assert blocker.state == BlockerState.ACTIVE

        blocker.deactivate()

    def it_transitions_to_inactive_on_deactivate(self) -> None:
        """Verify deactivate() transitions from ACTIVE to INACTIVE."""
        blocker = SleepPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        blocker.deactivate()

        assert blocker.state == BlockerState.INACTIVE

    def it_fails_to_activate_when_already_active(self) -> None:
        """Verify activate() raises when already ACTIVE."""
        blocker = SleepPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        try:
            with pytest.raises(ViolationError, match='INACTIVE'):
                blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        finally:
            blocker.reset()

    def it_fails_to_deactivate_when_inactive(self) -> None:
        """Verify deactivate() raises when already INACTIVE."""
        blocker = SleepPatchingBlocker()

        with pytest.raises(ViolationError, match='ACTIVE'):
            blocker.deactivate()

    def it_stores_activation_parameters(self) -> None:
        """Verify the blocker stores test size and enforcement mode."""
        blocker = SleepPatchingBlocker()

        blocker.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        assert blocker.current_test_size == TestSize.MEDIUM
        assert blocker.current_enforcement_mode == EnforcementMode.WARN

        blocker.deactivate()

    def it_blocks_all_sleep_calls_for_small_tests(self) -> None:
        """Verify small tests cannot use any sleep function."""
        blocker = SleepPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        assert blocker.check_sleep_allowed('time.sleep', 0.1) is False
        assert blocker.check_sleep_allowed('asyncio.sleep', 0.5) is False

        blocker.deactivate()

    def it_allows_all_sleep_calls_for_medium_tests(self) -> None:
        """Verify medium tests can use any sleep function."""
        blocker = SleepPatchingBlocker()
        blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)

        assert blocker.check_sleep_allowed('time.sleep', 0.1) is True
        assert blocker.check_sleep_allowed('asyncio.sleep', 1.0) is True

        blocker.deactivate()

    def it_allows_all_sleep_calls_for_large_tests(self) -> None:
        """Verify large tests can use any sleep function."""
        blocker = SleepPatchingBlocker()
        blocker.activate(TestSize.LARGE, EnforcementMode.STRICT)

        assert blocker.check_sleep_allowed('time.sleep', 0.1) is True

        blocker.deactivate()

    def it_raises_on_violation_in_strict_mode(self) -> None:
        """Verify on_violation raises SleepViolationError in STRICT mode."""
        blocker = SleepPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        with pytest.raises(SleepViolationError) as exc_info:
            blocker.on_violation('time.sleep', 0.1, 'test_module.py::test_fn')

        assert exc_info.value.function == 'time.sleep'
        assert exc_info.value.duration == 0.1

        blocker.deactivate()

    def it_resets_to_initial_state(self) -> None:
        """Verify reset() returns blocker to initial state."""
        blocker = SleepPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        blocker.reset()

        assert blocker.state == BlockerState.INACTIVE
        assert blocker.current_test_size is None
        assert blocker.current_enforcement_mode is None

    def it_patches_time_sleep_on_activate(self) -> None:
        """Verify time.sleep is patched when activated."""
        import time

        original_sleep = time.sleep
        blocker = SleepPatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        assert time.sleep is not original_sleep

        blocker.deactivate()

        assert time.sleep is original_sleep

    def it_restores_time_sleep_on_deactivate(self) -> None:
        """Verify time.sleep is restored when deactivated."""
        import time

        original_sleep = time.sleep
        blocker = SleepPatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        blocker.deactivate()

        assert time.sleep is original_sleep

    def it_restores_time_sleep_on_reset(self) -> None:
        """Verify time.sleep is restored on reset."""
        import time

        original_sleep = time.sleep
        blocker = SleepPatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        blocker.reset()

        assert time.sleep is original_sleep

    def it_patches_asyncio_sleep_on_activate(self) -> None:
        """Verify asyncio.sleep is patched when activated."""
        import asyncio

        original_sleep = asyncio.sleep
        blocker = SleepPatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        assert asyncio.sleep is not original_sleep

        blocker.deactivate()

        assert asyncio.sleep is original_sleep


@pytest.mark.small
class DescribeSleepViolationError:
    """Tests for the SleepViolationError exception."""

    def it_stores_function_and_duration(self) -> None:
        """Verify the exception stores function and duration."""
        error = SleepViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='test_module.py::test_fn',
            function='time.sleep',
            duration=0.1,
        )

        assert error.function == 'time.sleep'
        assert error.duration == 0.1

    def it_stores_test_context(self) -> None:
        """Verify the exception stores test size and nodeid."""
        error = SleepViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_timing.py::test_delay',
            function='time.sleep',
            duration=0.5,
        )

        assert error.test_size == TestSize.SMALL
        assert error.test_nodeid == 'tests/test_timing.py::test_delay'

    def it_includes_function_in_message(self) -> None:
        """Verify the error message includes the function."""
        error = SleepViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='test_module.py::test_fn',
            function='time.sleep',
            duration=0.1,
        )

        assert 'time.sleep' in str(error)

    def it_includes_duration_in_message(self) -> None:
        """Verify the error message includes the duration."""
        error = SleepViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='test_module.py::test_fn',
            function='time.sleep',
            duration=0.5,
        )

        assert '0.5' in str(error)

    def it_includes_remediation_for_small_tests(self) -> None:
        """Verify remediation suggestions are included for small tests."""
        error = SleepViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='test_module.py::test_fn',
            function='time.sleep',
            duration=0.1,
        )

        message = str(error)
        assert 'mock' in message.lower() or 'Mock' in message
        assert 'medium' in message.lower()

    def it_includes_asyncio_specific_remediation(self) -> None:
        """Verify asyncio-specific remediation is included."""
        error = SleepViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='test_module.py::test_fn',
            function='asyncio.sleep',
            duration=0.1,
        )

        message = str(error)
        assert 'asyncio.wait_for' in message

    def it_has_no_remediation_for_medium_tests(self) -> None:
        """Verify no remediation for medium tests since sleep is allowed."""
        error = SleepViolationError(
            test_size=TestSize.MEDIUM,
            test_nodeid='test_module.py::test_fn',
            function='time.sleep',
            duration=0.1,
        )

        assert error.remediation == []


@pytest.mark.small
class DescribeSleepAttempt:
    """Tests for the SleepAttempt model."""

    def it_is_immutable(self) -> None:
        """Verify SleepAttempt is frozen/immutable."""
        attempt = SleepAttempt(
            function='time.sleep',
            duration=0.1,
            test_nodeid='test::fn',
            allowed=False,
        )

        with pytest.raises(Exception):  # noqa: B017, PT011
            attempt.function = 'other'  # type: ignore[misc]

    def it_stores_all_fields(self) -> None:
        """Verify all fields are stored correctly."""
        attempt = SleepAttempt(
            function='asyncio.sleep',
            duration=0.5,
            test_nodeid='tests/test_timing.py::test_delay',
            allowed=True,
        )

        assert attempt.function == 'asyncio.sleep'
        assert attempt.duration == 0.5
        assert attempt.test_nodeid == 'tests/test_timing.py::test_delay'
        assert attempt.allowed is True

    def it_supports_equality(self) -> None:
        """Verify SleepAttempt supports equality comparison."""
        attempt1 = SleepAttempt(
            function='time.sleep',
            duration=0.1,
            test_nodeid='test::fn',
            allowed=False,
        )
        attempt2 = SleepAttempt(
            function='time.sleep',
            duration=0.1,
            test_nodeid='test::fn',
            allowed=False,
        )

        assert attempt1 == attempt2


@pytest.mark.small
class DescribeSleepPatchingBlockerBlocking:
    """Tests that verify sleep calls are blocked for small tests."""

    def it_blocks_time_sleep_for_small_tests(self) -> None:
        """Verify patched time.sleep raises SleepViolationError for small tests."""
        import time

        blocker = SleepPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        try:
            with pytest.raises(SleepViolationError) as exc_info:
                time.sleep(0.1)

            assert exc_info.value.function == 'time.sleep'
            assert exc_info.value.duration == 0.1
        finally:
            blocker.deactivate()

    def it_blocks_time_sleep_with_zero_duration_for_small_tests(self) -> None:
        """Verify patched time.sleep raises even for zero duration."""
        import time

        blocker = SleepPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        try:
            with pytest.raises(SleepViolationError) as exc_info:
                time.sleep(0)

            assert exc_info.value.function == 'time.sleep'
            assert exc_info.value.duration == 0
        finally:
            blocker.deactivate()


@pytest.mark.medium
class DescribeSleepPatchingBlockerIntegration:
    """Integration tests that actually execute sleep calls for medium tests."""

    def it_allows_time_sleep_for_medium_tests(self) -> None:
        """Verify patched time.sleep delegates to original for medium tests."""
        import time

        blocker = SleepPatchingBlocker()
        blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)

        try:
            start = time.perf_counter()
            time.sleep(0.01)  # Very short sleep
            elapsed = time.perf_counter() - start

            # Should have slept for at least some time
            assert elapsed >= 0.005
        finally:
            blocker.deactivate()

    def it_allows_time_sleep_for_large_tests(self) -> None:
        """Verify patched time.sleep delegates to original for large tests."""
        import time

        blocker = SleepPatchingBlocker()
        blocker.activate(TestSize.LARGE, EnforcementMode.STRICT)

        try:
            start = time.perf_counter()
            time.sleep(0.01)
            elapsed = time.perf_counter() - start

            assert elapsed >= 0.005
        finally:
            blocker.deactivate()

    def it_allows_asyncio_sleep_for_medium_tests(self) -> None:
        """Verify patched asyncio.sleep delegates to original for medium tests."""
        import asyncio
        import time

        async def run_test() -> float:
            blocker = SleepPatchingBlocker()
            blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)

            try:
                start = time.perf_counter()
                await asyncio.sleep(0.01)
                return time.perf_counter() - start
            finally:
                blocker.deactivate()

        elapsed = asyncio.run(run_test())
        assert elapsed >= 0.005

    def it_blocks_asyncio_sleep_for_small_tests(self) -> None:
        """Verify patched asyncio.sleep raises SleepViolationError for small tests."""
        import asyncio

        async def run_test() -> SleepViolationError:
            blocker = SleepPatchingBlocker()
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

            try:
                with pytest.raises(SleepViolationError) as exc_info:
                    await asyncio.sleep(0.1)
                return exc_info.value
            finally:
                blocker.deactivate()

        error = asyncio.run(run_test())
        assert error.function == 'asyncio.sleep'
        assert error.duration == 0.1
