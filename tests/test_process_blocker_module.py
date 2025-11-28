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


@pytest.mark.small
class DescribeExtractCommandAndArgs:
    """Tests for the _extract_command_and_args method."""

    def it_extracts_command_from_list(self) -> None:
        """Verify list input extracts command and args."""
        blocker = SubprocessPatchingBlocker()

        command, args = blocker._extract_command_and_args(['python', 'script.py', '--verbose'])

        assert command == 'python'
        assert args == ('script.py', '--verbose')

    def it_extracts_command_from_string(self) -> None:
        """Verify string input returns command with empty args."""
        blocker = SubprocessPatchingBlocker()

        command, args = blocker._extract_command_and_args('python script.py')

        assert command == 'python script.py'
        assert args == ()

    def it_handles_empty_list(self) -> None:
        """Verify empty list returns stringified input with empty args."""
        blocker = SubprocessPatchingBlocker()

        command, args = blocker._extract_command_and_args([])

        assert command == '[]'
        assert args == ()

    def it_handles_none_input(self) -> None:
        """Verify None input returns stringified None with empty args."""
        blocker = SubprocessPatchingBlocker()

        command, args = blocker._extract_command_and_args(None)

        assert command == 'None'
        assert args == ()

    def it_handles_single_item_list(self) -> None:
        """Verify single item list extracts command with no args."""
        blocker = SubprocessPatchingBlocker()

        command, args = blocker._extract_command_and_args(['python'])

        assert command == 'python'
        assert args == ()

    def it_handles_tuple_input(self) -> None:
        """Verify tuple input extracts command and args."""
        blocker = SubprocessPatchingBlocker()

        command, args = blocker._extract_command_and_args(('echo', 'hello', 'world'))

        assert command == 'echo'
        assert args == ('hello', 'world')


@pytest.mark.small
class DescribeSubprocessPatchingBlockerBlocking:
    """Tests that verify subprocess calls are blocked for small tests."""

    def it_blocks_subprocess_popen_for_small_tests(self) -> None:
        """Verify patched subprocess.Popen raises SubprocessViolationError for small tests."""
        blocker = SubprocessPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        try:
            with pytest.raises(SubprocessViolationError) as exc_info:
                subprocess.Popen(['echo', 'test'])  # noqa: S607

            assert exc_info.value.method == 'subprocess.Popen'
            assert exc_info.value.command == 'echo'
        finally:
            blocker.deactivate()

    def it_blocks_subprocess_run_for_small_tests(self) -> None:
        """Verify patched subprocess.run raises SubprocessViolationError for small tests."""
        blocker = SubprocessPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        try:
            with pytest.raises(SubprocessViolationError) as exc_info:
                subprocess.run(['echo', 'test'], check=False)  # noqa: S607

            assert exc_info.value.method == 'subprocess.run'
            assert exc_info.value.command == 'echo'
        finally:
            blocker.deactivate()

    def it_blocks_subprocess_call_for_small_tests(self) -> None:
        """Verify patched subprocess.call raises SubprocessViolationError for small tests."""
        blocker = SubprocessPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        try:
            with pytest.raises(SubprocessViolationError) as exc_info:
                subprocess.call(['echo', 'test'])  # noqa: S607

            assert exc_info.value.method == 'subprocess.call'
        finally:
            blocker.deactivate()

    def it_blocks_subprocess_check_call_for_small_tests(self) -> None:
        """Verify patched subprocess.check_call raises SubprocessViolationError for small tests."""
        blocker = SubprocessPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        try:
            with pytest.raises(SubprocessViolationError) as exc_info:
                subprocess.check_call(['echo', 'test'])  # noqa: S607

            assert exc_info.value.method == 'subprocess.check_call'
        finally:
            blocker.deactivate()

    def it_blocks_subprocess_check_output_for_small_tests(self) -> None:
        """Verify patched subprocess.check_output raises SubprocessViolationError for small tests."""
        blocker = SubprocessPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        try:
            with pytest.raises(SubprocessViolationError) as exc_info:
                subprocess.check_output(['echo', 'test'])  # noqa: S607

            assert exc_info.value.method == 'subprocess.check_output'
        finally:
            blocker.deactivate()

    def it_blocks_os_system_for_small_tests(self) -> None:
        """Verify patched os.system raises SubprocessViolationError for small tests."""
        blocker = SubprocessPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        try:
            with pytest.raises(SubprocessViolationError) as exc_info:
                os.system('echo test')  # noqa: S605, S607

            assert exc_info.value.method == 'os.system'
        finally:
            blocker.deactivate()

    def it_blocks_os_popen_for_small_tests(self) -> None:
        """Verify patched os.popen raises SubprocessViolationError for small tests."""
        blocker = SubprocessPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        try:
            with pytest.raises(SubprocessViolationError) as exc_info:
                os.popen('echo test')  # noqa: S605, S607

            assert exc_info.value.method == 'os.popen'
        finally:
            blocker.deactivate()

    def it_blocks_multiprocessing_process_for_small_tests(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify patched multiprocessing.Process.start raises SubprocessViolationError for small tests."""
        original_process = multiprocessing.Process
        blocker = SubprocessPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        try:

            def dummy_target() -> None:
                pass

            proc = multiprocessing.Process(target=dummy_target)

            # Mock the original start method so we don't actually spawn
            # The violation should happen before super().start() is called
            monkeypatch.setattr(original_process, 'start', lambda self: None)  # noqa: ARG005

            with pytest.raises(SubprocessViolationError) as exc_info:
                proc.start()

            assert exc_info.value.method == 'multiprocessing.Process'
            assert exc_info.value.command == 'dummy_target'
        finally:
            blocker.deactivate()


@pytest.mark.medium
class DescribeSubprocessPatchingBlockerIntegration:
    """Integration tests that actually execute subprocess calls for medium tests."""

    def it_allows_subprocess_run_for_medium_tests(self) -> None:
        """Verify patched subprocess.run delegates to original for medium tests."""
        blocker = SubprocessPatchingBlocker()
        blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)

        try:
            result = subprocess.run(['echo', 'test'], capture_output=True, text=True, check=False)  # noqa: S607

            assert 'test' in result.stdout
        finally:
            blocker.deactivate()

    def it_allows_subprocess_call_for_medium_tests(self) -> None:
        """Verify patched subprocess.call delegates to original for medium tests."""
        blocker = SubprocessPatchingBlocker()
        blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)

        try:
            exit_code = subprocess.call(['true'])  # noqa: S607

            assert exit_code == 0
        finally:
            blocker.deactivate()

    def it_allows_subprocess_check_call_for_medium_tests(self) -> None:
        """Verify patched subprocess.check_call delegates to original for medium tests."""
        blocker = SubprocessPatchingBlocker()
        blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)

        try:
            subprocess.check_call(['true'])  # noqa: S607
        finally:
            blocker.deactivate()

    def it_allows_subprocess_check_output_for_medium_tests(self) -> None:
        """Verify patched subprocess.check_output delegates to original for medium tests."""
        blocker = SubprocessPatchingBlocker()
        blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)

        try:
            output = subprocess.check_output(['echo', 'hello'], text=True)  # noqa: S607

            assert 'hello' in output
        finally:
            blocker.deactivate()

    def it_allows_subprocess_popen_for_medium_tests(self) -> None:
        """Verify patched subprocess.Popen delegates to original for medium tests."""
        blocker = SubprocessPatchingBlocker()
        blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)

        try:
            proc = subprocess.Popen(
                ['echo', 'popen_test'],  # noqa: S607
                stdout=subprocess.PIPE,
                text=True,
            )
            stdout, _ = proc.communicate()

            assert 'popen_test' in stdout
        finally:
            blocker.deactivate()

    def it_allows_os_system_for_medium_tests(self) -> None:
        """Verify patched os.system delegates to original for medium tests."""
        blocker = SubprocessPatchingBlocker()
        blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)

        try:
            exit_code = os.system('true')  # noqa: S605, S607

            assert exit_code == 0
        finally:
            blocker.deactivate()

    def it_allows_os_popen_for_medium_tests(self) -> None:
        """Verify patched os.popen delegates to original for medium tests."""
        blocker = SubprocessPatchingBlocker()
        blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)

        try:
            pipe = os.popen('echo popen_os_test')  # noqa: S605, S607
            output = pipe.read()
            pipe.close()

            assert 'popen_os_test' in output
        finally:
            blocker.deactivate()

    def it_allows_multiprocessing_process_for_medium_tests(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify patched multiprocessing.Process.start delegates to original for medium tests.

        We mock the actual process start to avoid macOS spawn/pickling issues while
        still testing the blocking logic path for MEDIUM tests.
        """
        # Store references to original classes before patching
        original_process = multiprocessing.Process

        blocker = SubprocessPatchingBlocker()
        blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)

        try:

            def dummy_target() -> None:
                pass

            # Create a process using the patched BlockingProcess
            proc = multiprocessing.Process(target=dummy_target)

            # Track whether super().start() was called
            start_called = []

            def mock_start(self: multiprocessing.Process) -> None:  # noqa: ARG001
                start_called.append(True)

            # Mock the original Process's start method to avoid pickling
            # The BlockingProcess.start() calls super().start() which we mock
            monkeypatch.setattr(original_process, 'start', mock_start)

            # Call start - this should go through BlockingProcess.start(), check permissions,
            # and then call super().start() (which is now mocked)
            proc.start()

            # Verify super().start() was called (meaning blocking logic allowed it)
            assert len(start_called) == 1
        finally:
            blocker.deactivate()
