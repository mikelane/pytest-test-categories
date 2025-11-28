"""Test the process blocker adapters.

This module tests both the FakeProcessBlocker (test adapter) and
SubprocessPatchingBlocker (production adapter) implementations.

The process blockers follow hexagonal architecture:
- ProcessBlockerPort is the Port (interface)
- FakeProcessBlocker is a Test Adapter (test double)
- SubprocessPatchingBlocker is a Production Adapter (real implementation)

This follows the same pattern as the network and filesystem blocker modules.

Note: S108 warnings about /tmp paths are suppressed because these are symbolic
test values for testing argument handling, not actual insecure temp file usage.
"""
# ruff: noqa: S108

from __future__ import annotations

import multiprocessing
import os
import subprocess

import pytest
from icontract import ViolationError

from pytest_test_categories.adapters.fake_process import FakeProcessBlocker
from pytest_test_categories.adapters.process import SubprocessPatchingBlocker
from pytest_test_categories.exceptions import SubprocessViolationError
from pytest_test_categories.ports.network import (
    BlockerState,
    EnforcementMode,
)
from pytest_test_categories.ports.process import SpawnAttempt
from pytest_test_categories.types import TestSize


@pytest.mark.small
class DescribeFakeProcessBlocker:
    """Tests for the FakeProcessBlocker test double."""

    def it_starts_in_inactive_state(self) -> None:
        """Verify the blocker initializes in INACTIVE state."""
        blocker = FakeProcessBlocker()

        assert blocker.state == BlockerState.INACTIVE

    def it_transitions_to_active_on_activate(self) -> None:
        """Verify activate() transitions from INACTIVE to ACTIVE."""
        blocker = FakeProcessBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        assert blocker.state == BlockerState.ACTIVE

    def it_transitions_to_inactive_on_deactivate(self) -> None:
        """Verify deactivate() transitions from ACTIVE to INACTIVE."""
        blocker = FakeProcessBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        blocker.deactivate()

        assert blocker.state == BlockerState.INACTIVE

    def it_fails_to_activate_when_already_active(self) -> None:
        """Verify activate() raises when already ACTIVE."""
        blocker = FakeProcessBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        with pytest.raises(ViolationError, match='INACTIVE'):
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

    def it_fails_to_deactivate_when_inactive(self) -> None:
        """Verify deactivate() raises when already INACTIVE."""
        blocker = FakeProcessBlocker()

        with pytest.raises(ViolationError, match='ACTIVE'):
            blocker.deactivate()

    def it_records_activation_parameters(self) -> None:
        """Verify the blocker records test size and enforcement mode."""
        blocker = FakeProcessBlocker()

        blocker.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        assert blocker.current_test_size == TestSize.MEDIUM
        assert blocker.current_enforcement_mode == EnforcementMode.WARN

    def it_blocks_all_spawns_for_small_tests(self) -> None:
        """Verify small tests cannot spawn any processes."""
        blocker = FakeProcessBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        assert blocker.check_spawn_allowed('python', ('script.py',)) is False
        assert blocker.check_spawn_allowed('ls', ('-la',)) is False
        assert blocker.check_spawn_allowed('echo', ('hello',)) is False

    def it_allows_all_spawns_for_medium_tests(self) -> None:
        """Verify medium tests can spawn processes."""
        blocker = FakeProcessBlocker()
        blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)

        assert blocker.check_spawn_allowed('python', ('script.py',)) is True
        assert blocker.check_spawn_allowed('pytest', ('tests/',)) is True

    def it_allows_all_spawns_for_large_tests(self) -> None:
        """Verify large tests can spawn processes."""
        blocker = FakeProcessBlocker()
        blocker.activate(TestSize.LARGE, EnforcementMode.STRICT)

        assert blocker.check_spawn_allowed('python', ('script.py',)) is True
        assert blocker.check_spawn_allowed('docker', ('run', 'image')) is True

    def it_allows_all_spawns_for_xlarge_tests(self) -> None:
        """Verify xlarge tests can spawn processes."""
        blocker = FakeProcessBlocker()
        blocker.activate(TestSize.XLARGE, EnforcementMode.STRICT)

        assert blocker.check_spawn_allowed('python', ('script.py',)) is True
        assert blocker.check_spawn_allowed('kubectl', ('apply', '-f', 'manifest.yaml')) is True

    def it_records_spawn_attempts(self) -> None:
        """Verify the blocker tracks process spawn attempts."""
        blocker = FakeProcessBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        blocker.check_spawn_allowed('python', ('script.py',))
        blocker.check_spawn_allowed('ls', ('-la', '/tmp'))

        assert len(blocker.spawn_attempts) == 2
        assert blocker.spawn_attempts[0] == SpawnAttempt(
            command='python',
            args=('script.py',),
            test_nodeid='',
            allowed=False,
            method='check_spawn_allowed',
        )
        assert blocker.spawn_attempts[1] == SpawnAttempt(
            command='ls',
            args=('-la', '/tmp'),
            test_nodeid='',
            allowed=False,
            method='check_spawn_allowed',
        )

    def it_raises_on_violation_in_strict_mode(self) -> None:
        """Verify on_violation raises SubprocessViolationError in STRICT mode."""
        blocker = FakeProcessBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        with pytest.raises(SubprocessViolationError) as exc_info:
            blocker.on_violation('python', ('script.py',), 'test_module.py::test_fn', 'subprocess.run')

        assert exc_info.value.command == 'python'
        assert exc_info.value.command_args == ('script.py',)
        assert exc_info.value.method == 'subprocess.run'
        assert exc_info.value.test_size == TestSize.SMALL

    def it_records_warning_in_warn_mode(self) -> None:
        """Verify on_violation records warning in WARN mode."""
        blocker = FakeProcessBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.WARN)

        blocker.on_violation('python', ('script.py',), 'test_module.py::test_fn', 'subprocess.run')

        assert len(blocker.warnings) == 1
        assert 'python' in blocker.warnings[0]
        assert 'subprocess.run' in blocker.warnings[0]

    def it_does_nothing_in_off_mode(self) -> None:
        """Verify on_violation does nothing in OFF mode."""
        blocker = FakeProcessBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.OFF)

        blocker.on_violation('python', ('script.py',), 'test_module.py::test_fn', 'subprocess.run')

        assert len(blocker.warnings) == 0

    def it_fails_check_spawn_when_inactive(self) -> None:
        """Verify check_spawn_allowed raises when INACTIVE."""
        blocker = FakeProcessBlocker()

        with pytest.raises(ViolationError, match='ACTIVE'):
            blocker.check_spawn_allowed('python', ('script.py',))

    def it_fails_on_violation_when_inactive(self) -> None:
        """Verify on_violation raises when INACTIVE."""
        blocker = FakeProcessBlocker()

        with pytest.raises(ViolationError, match='ACTIVE'):
            blocker.on_violation('python', ('script.py',), 'test::fn', 'subprocess.run')

    def it_resets_to_initial_state(self) -> None:
        """Verify reset() returns blocker to initial state."""
        blocker = FakeProcessBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        blocker.check_spawn_allowed('python', ('script.py',))

        blocker.reset()

        assert blocker.state == BlockerState.INACTIVE
        assert blocker.current_test_size is None
        assert blocker.current_enforcement_mode is None
        assert len(blocker.spawn_attempts) == 0
        assert len(blocker.warnings) == 0

    def it_resets_even_when_active(self) -> None:
        """Verify reset() works regardless of current state."""
        blocker = FakeProcessBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        blocker.reset()

        assert blocker.state == BlockerState.INACTIVE

    def it_tracks_call_counts(self) -> None:
        """Verify the blocker tracks method invocation counts."""
        blocker = FakeProcessBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        blocker.check_spawn_allowed('cmd1', ())
        blocker.check_spawn_allowed('cmd2', ())
        blocker.deactivate()

        assert blocker.activate_count == 1
        assert blocker.deactivate_count == 1
        assert blocker.check_count == 2


@pytest.mark.small
class DescribeSubprocessPatchingBlocker:
    """Tests for the SubprocessPatchingBlocker production adapter."""

    def it_starts_in_inactive_state(self) -> None:
        """Verify the blocker initializes in INACTIVE state."""
        blocker = SubprocessPatchingBlocker()

        assert blocker.state == BlockerState.INACTIVE

    def it_transitions_to_active_on_activate(self) -> None:
        """Verify activate() transitions from INACTIVE to ACTIVE."""
        blocker = SubprocessPatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        assert blocker.state == BlockerState.ACTIVE

        blocker.deactivate()

    def it_transitions_to_inactive_on_deactivate(self) -> None:
        """Verify deactivate() transitions from ACTIVE to INACTIVE."""
        blocker = SubprocessPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        blocker.deactivate()

        assert blocker.state == BlockerState.INACTIVE

    def it_fails_to_activate_when_already_active(self) -> None:
        """Verify activate() raises when already ACTIVE."""
        blocker = SubprocessPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        try:
            with pytest.raises(ViolationError, match='INACTIVE'):
                blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        finally:
            blocker.reset()

    def it_fails_to_deactivate_when_inactive(self) -> None:
        """Verify deactivate() raises when already INACTIVE."""
        blocker = SubprocessPatchingBlocker()

        with pytest.raises(ViolationError, match='ACTIVE'):
            blocker.deactivate()

    def it_stores_activation_parameters(self) -> None:
        """Verify the blocker stores test size and enforcement mode."""
        blocker = SubprocessPatchingBlocker()

        blocker.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        assert blocker.current_test_size == TestSize.MEDIUM
        assert blocker.current_enforcement_mode == EnforcementMode.WARN

        blocker.deactivate()

    def it_blocks_all_spawns_for_small_tests(self) -> None:
        """Verify small tests cannot spawn any processes."""
        blocker = SubprocessPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        assert blocker.check_spawn_allowed('python', ('script.py',)) is False
        assert blocker.check_spawn_allowed('ls', ('-la',)) is False

        blocker.deactivate()

    def it_allows_all_spawns_for_medium_tests(self) -> None:
        """Verify medium tests can spawn processes."""
        blocker = SubprocessPatchingBlocker()
        blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)

        assert blocker.check_spawn_allowed('python', ('script.py',)) is True
        assert blocker.check_spawn_allowed('pytest', ('tests/',)) is True

        blocker.deactivate()

    def it_allows_all_spawns_for_large_tests(self) -> None:
        """Verify large tests can spawn processes."""
        blocker = SubprocessPatchingBlocker()
        blocker.activate(TestSize.LARGE, EnforcementMode.STRICT)

        assert blocker.check_spawn_allowed('python', ('script.py',)) is True

        blocker.deactivate()

    def it_raises_on_violation_in_strict_mode(self) -> None:
        """Verify on_violation raises SubprocessViolationError in STRICT mode."""
        blocker = SubprocessPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        with pytest.raises(SubprocessViolationError) as exc_info:
            blocker.on_violation('python', ('script.py',), 'test_module.py::test_fn', 'subprocess.run')

        assert exc_info.value.command == 'python'
        assert exc_info.value.command_args == ('script.py',)

        blocker.deactivate()

    def it_resets_to_initial_state(self) -> None:
        """Verify reset() returns blocker to initial state."""
        blocker = SubprocessPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        blocker.reset()

        assert blocker.state == BlockerState.INACTIVE
        assert blocker.current_test_size is None
        assert blocker.current_enforcement_mode is None

    def it_patches_subprocess_popen_on_activate(self) -> None:
        """Verify subprocess.Popen is patched when activated."""
        original_popen = subprocess.Popen
        blocker = SubprocessPatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        assert subprocess.Popen is not original_popen

        blocker.deactivate()

        assert subprocess.Popen is original_popen

    def it_patches_subprocess_run_on_activate(self) -> None:
        """Verify subprocess.run is patched when activated."""
        original_run = subprocess.run
        blocker = SubprocessPatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        assert subprocess.run is not original_run

        blocker.deactivate()

        assert subprocess.run is original_run

    def it_patches_subprocess_call_on_activate(self) -> None:
        """Verify subprocess.call is patched when activated."""
        original_call = subprocess.call
        blocker = SubprocessPatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        assert subprocess.call is not original_call

        blocker.deactivate()

        assert subprocess.call is original_call

    def it_patches_subprocess_check_call_on_activate(self) -> None:
        """Verify subprocess.check_call is patched when activated."""
        original_check_call = subprocess.check_call
        blocker = SubprocessPatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        assert subprocess.check_call is not original_check_call

        blocker.deactivate()

        assert subprocess.check_call is original_check_call

    def it_patches_subprocess_check_output_on_activate(self) -> None:
        """Verify subprocess.check_output is patched when activated."""
        original_check_output = subprocess.check_output
        blocker = SubprocessPatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        assert subprocess.check_output is not original_check_output

        blocker.deactivate()

        assert subprocess.check_output is original_check_output

    def it_patches_os_system_on_activate(self) -> None:
        """Verify os.system is patched when activated."""
        original_os_system = os.system
        blocker = SubprocessPatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        assert os.system is not original_os_system

        blocker.deactivate()

        assert os.system is original_os_system

    def it_patches_os_popen_on_activate(self) -> None:
        """Verify os.popen is patched when activated."""
        original_os_popen = os.popen
        blocker = SubprocessPatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        assert os.popen is not original_os_popen

        blocker.deactivate()

        assert os.popen is original_os_popen

    def it_patches_multiprocessing_process_on_activate(self) -> None:
        """Verify multiprocessing.Process is patched when activated."""
        original_mp_process = multiprocessing.Process
        blocker = SubprocessPatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        assert multiprocessing.Process is not original_mp_process

        blocker.deactivate()

        assert multiprocessing.Process is original_mp_process

    def it_restores_all_functions_on_reset(self) -> None:
        """Verify all patched functions are restored on reset."""
        original_popen = subprocess.Popen
        original_run = subprocess.run
        original_os_system = os.system
        blocker = SubprocessPatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        blocker.reset()

        assert subprocess.Popen is original_popen
        assert subprocess.run is original_run
        assert os.system is original_os_system


@pytest.mark.small
class DescribeSubprocessViolationError:
    """Tests for the SubprocessViolationError exception."""

    def it_stores_command_and_args(self) -> None:
        """Verify the exception stores command and args."""
        error = SubprocessViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='test_module.py::test_fn',
            command='python',
            command_args=('script.py', '--verbose'),
            method='subprocess.run',
        )

        assert error.command == 'python'
        assert error.command_args == ('script.py', '--verbose')
        assert error.method == 'subprocess.run'

    def it_stores_test_context(self) -> None:
        """Verify the exception stores test size and nodeid."""
        error = SubprocessViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_cli.py::test_run',
            command='bash',
            command_args=('-c', 'echo hello'),
            method='os.system',
        )

        assert error.test_size == TestSize.SMALL
        assert error.test_nodeid == 'tests/test_cli.py::test_run'

    def it_includes_command_in_message(self) -> None:
        """Verify the error message includes the command."""
        error = SubprocessViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='test_module.py::test_fn',
            command='python',
            command_args=('script.py',),
            method='subprocess.run',
        )

        assert 'python' in str(error)
        assert 'subprocess.run' in str(error)

    def it_includes_remediation_for_small_tests(self) -> None:
        """Verify remediation suggestions are included for small tests."""
        error = SubprocessViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='test_module.py::test_fn',
            command='python',
            command_args=('script.py',),
            method='subprocess.run',
        )

        message = str(error)
        assert 'Mock' in message or 'mock' in message
        assert 'medium' in message.lower()

    def it_handles_empty_args(self) -> None:
        """Verify the exception handles empty args gracefully."""
        error = SubprocessViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='test_module.py::test_fn',
            command='ls',
            command_args=(),
            method='subprocess.run',
        )

        assert 'no args' in str(error).lower()


@pytest.mark.small
class DescribeSpawnAttempt:
    """Tests for the SpawnAttempt model."""

    def it_is_immutable(self) -> None:
        """Verify SpawnAttempt is frozen/immutable."""
        attempt = SpawnAttempt(
            command='python',
            args=('script.py',),
            test_nodeid='test::fn',
            allowed=False,
            method='subprocess.run',
        )

        with pytest.raises(Exception):  # noqa: B017, PT011
            attempt.command = 'other'  # type: ignore[misc]

    def it_stores_all_fields(self) -> None:
        """Verify all fields are stored correctly."""
        attempt = SpawnAttempt(
            command='python',
            args=('script.py', '--verbose'),
            test_nodeid='tests/test_cli.py::test_run',
            allowed=True,
            method='subprocess.Popen',
        )

        assert attempt.command == 'python'
        assert attempt.args == ('script.py', '--verbose')
        assert attempt.test_nodeid == 'tests/test_cli.py::test_run'
        assert attempt.allowed is True
        assert attempt.method == 'subprocess.Popen'

    def it_supports_equality(self) -> None:
        """Verify SpawnAttempt supports equality comparison."""
        attempt1 = SpawnAttempt(
            command='python',
            args=('script.py',),
            test_nodeid='test::fn',
            allowed=False,
            method='subprocess.run',
        )
        attempt2 = SpawnAttempt(
            command='python',
            args=('script.py',),
            test_nodeid='test::fn',
            allowed=False,
            method='subprocess.run',
        )

        assert attempt1 == attempt2
