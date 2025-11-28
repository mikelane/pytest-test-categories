"""Test the filesystem blocker adapters.

This module tests both the FakeFilesystemBlocker (test adapter) and
FilesystemPatchingBlocker (production adapter) implementations.

The filesystem blockers follow hexagonal architecture:
- FilesystemBlockerPort is the Port (interface)
- FakeFilesystemBlocker is a Test Adapter (test double)
- FilesystemPatchingBlocker is a Production Adapter (real implementation)

This follows the same pattern as the network blocker module.

Note: S108 warnings about /tmp paths are suppressed because these are symbolic
test values for testing path matching logic, not actual insecure temp file usage.
"""
# ruff: noqa: S108

from __future__ import annotations

from pathlib import Path

import pytest
from icontract import ViolationError

from pytest_test_categories.adapters.fake_filesystem import FakeFilesystemBlocker
from pytest_test_categories.adapters.filesystem import FilesystemPatchingBlocker
from pytest_test_categories.exceptions import FilesystemAccessViolationError
from pytest_test_categories.ports.filesystem import (
    FilesystemAccessAttempt,
    FilesystemOperation,
)
from pytest_test_categories.ports.network import (
    BlockerState,
    EnforcementMode,
)
from pytest_test_categories.types import TestSize


@pytest.mark.medium
class DescribeFakeFilesystemBlocker:
    """Tests for the FakeFilesystemBlocker test double.

    Note: Marked as medium due to timing variability with icontract ViolationError
    on CI environments (specifically macOS + Python 3.11). The icontract library
    performs introspection and string formatting when raising violations, which can
    exceed the 1-second small test limit under CI load conditions.
    """

    def it_starts_in_inactive_state(self) -> None:
        """Verify the blocker initializes in INACTIVE state."""
        blocker = FakeFilesystemBlocker()

        assert blocker.state == BlockerState.INACTIVE

    def it_transitions_to_active_on_activate(self) -> None:
        """Verify activate() transitions from INACTIVE to ACTIVE."""
        blocker = FakeFilesystemBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

        assert blocker.state == BlockerState.ACTIVE

    def it_transitions_to_inactive_on_deactivate(self) -> None:
        """Verify deactivate() transitions from ACTIVE to INACTIVE."""
        blocker = FakeFilesystemBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

        blocker.deactivate()

        assert blocker.state == BlockerState.INACTIVE

    def it_fails_to_activate_when_already_active(self) -> None:
        """Verify activate() raises when already ACTIVE."""
        blocker = FakeFilesystemBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

        with pytest.raises(ViolationError, match='INACTIVE'):
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

    def it_fails_to_deactivate_when_inactive(self) -> None:
        """Verify deactivate() raises when already INACTIVE."""
        blocker = FakeFilesystemBlocker()

        with pytest.raises(ViolationError, match='ACTIVE'):
            blocker.deactivate()

    def it_records_activation_parameters(self) -> None:
        """Verify the blocker records test size, enforcement mode, and allowed paths."""
        blocker = FakeFilesystemBlocker()
        allowed = frozenset([Path('/tmp')])

        blocker.activate(TestSize.MEDIUM, EnforcementMode.WARN, allowed)

        assert blocker.current_test_size == TestSize.MEDIUM
        assert blocker.current_enforcement_mode == EnforcementMode.WARN
        assert blocker.current_allowed_paths == allowed

    def it_blocks_all_access_for_small_tests_without_allowed_paths(self) -> None:
        """Verify small tests cannot access any filesystem without allowed paths."""
        blocker = FakeFilesystemBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

        assert blocker.check_access_allowed(Path('/etc/passwd'), FilesystemOperation.READ) is False
        assert blocker.check_access_allowed(Path('/home/user/file.txt'), FilesystemOperation.WRITE) is False
        assert blocker.check_access_allowed(Path('/tmp/test'), FilesystemOperation.CREATE) is False

    def it_allows_access_to_allowed_paths_for_small_tests(self) -> None:
        """Verify small tests can access allowed paths."""
        allowed = frozenset([Path('/tmp').resolve()])
        blocker = FakeFilesystemBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, allowed)

        assert blocker.check_access_allowed(Path('/tmp/test.txt'), FilesystemOperation.WRITE) is True
        assert blocker.check_access_allowed(Path('/tmp/subdir/file.txt'), FilesystemOperation.READ) is True

    def it_blocks_access_outside_allowed_paths_for_small_tests(self) -> None:
        """Verify small tests cannot access paths outside allowed paths."""
        allowed = frozenset([Path('/tmp').resolve()])
        blocker = FakeFilesystemBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, allowed)

        assert blocker.check_access_allowed(Path('/etc/passwd'), FilesystemOperation.READ) is False
        assert blocker.check_access_allowed(Path('/home/user/file.txt'), FilesystemOperation.WRITE) is False

    def it_allows_all_access_for_medium_tests(self) -> None:
        """Verify medium tests can access any filesystem."""
        blocker = FakeFilesystemBlocker()
        blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT, frozenset())

        assert blocker.check_access_allowed(Path('/etc/passwd'), FilesystemOperation.READ) is True
        assert blocker.check_access_allowed(Path('/home/user/file.txt'), FilesystemOperation.WRITE) is True

    def it_allows_all_access_for_large_tests(self) -> None:
        """Verify large tests can access any filesystem."""
        blocker = FakeFilesystemBlocker()
        blocker.activate(TestSize.LARGE, EnforcementMode.STRICT, frozenset())

        assert blocker.check_access_allowed(Path('/etc/passwd'), FilesystemOperation.READ) is True
        assert blocker.check_access_allowed(Path('/any/path'), FilesystemOperation.DELETE) is True

    def it_allows_all_access_for_xlarge_tests(self) -> None:
        """Verify xlarge tests can access any filesystem."""
        blocker = FakeFilesystemBlocker()
        blocker.activate(TestSize.XLARGE, EnforcementMode.STRICT, frozenset())

        assert blocker.check_access_allowed(Path('/etc/passwd'), FilesystemOperation.READ) is True
        assert blocker.check_access_allowed(Path('/any/path'), FilesystemOperation.MODIFY) is True

    def it_records_access_attempts(self) -> None:
        """Verify the blocker tracks filesystem access attempts."""
        blocker = FakeFilesystemBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

        blocker.check_access_allowed(Path('/etc/passwd'), FilesystemOperation.READ)
        blocker.check_access_allowed(Path('/tmp/test.txt'), FilesystemOperation.WRITE)

        assert len(blocker.access_attempts) == 2
        assert blocker.access_attempts[0] == FilesystemAccessAttempt(
            path=Path('/etc/passwd'),
            operation=FilesystemOperation.READ,
            test_nodeid='',
            allowed=False,
        )
        assert blocker.access_attempts[1] == FilesystemAccessAttempt(
            path=Path('/tmp/test.txt'),
            operation=FilesystemOperation.WRITE,
            test_nodeid='',
            allowed=False,
        )

    def it_raises_on_violation_in_strict_mode(self) -> None:
        """Verify on_violation raises FilesystemAccessViolationError in STRICT mode."""
        blocker = FakeFilesystemBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

        with pytest.raises(FilesystemAccessViolationError) as exc_info:
            blocker.on_violation(Path('/etc/passwd'), FilesystemOperation.READ, 'test_module.py::test_fn')

        assert exc_info.value.path == Path('/etc/passwd')
        assert exc_info.value.operation == FilesystemOperation.READ
        assert exc_info.value.test_size == TestSize.SMALL

    def it_records_warning_in_warn_mode(self) -> None:
        """Verify on_violation records warning in WARN mode."""
        blocker = FakeFilesystemBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.WARN, frozenset())
        test_path = Path('/etc/passwd')

        blocker.on_violation(test_path, FilesystemOperation.READ, 'test_module.py::test_fn')

        assert len(blocker.warnings) == 1
        assert str(test_path) in blocker.warnings[0]
        assert 'read' in blocker.warnings[0]

    def it_does_nothing_in_off_mode(self) -> None:
        """Verify on_violation does nothing in OFF mode."""
        blocker = FakeFilesystemBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.OFF, frozenset())

        blocker.on_violation(Path('/etc/passwd'), FilesystemOperation.READ, 'test_module.py::test_fn')

        assert len(blocker.warnings) == 0

    def it_fails_check_access_when_inactive(self) -> None:
        """Verify check_access_allowed raises when INACTIVE."""
        blocker = FakeFilesystemBlocker()

        with pytest.raises(ViolationError, match='ACTIVE'):
            blocker.check_access_allowed(Path('/tmp'), FilesystemOperation.READ)

    def it_fails_on_violation_when_inactive(self) -> None:
        """Verify on_violation raises when INACTIVE."""
        blocker = FakeFilesystemBlocker()

        with pytest.raises(ViolationError, match='ACTIVE'):
            blocker.on_violation(Path('/tmp'), FilesystemOperation.READ, 'test::fn')

    def it_resets_to_initial_state(self) -> None:
        """Verify reset() returns blocker to initial state."""
        blocker = FakeFilesystemBlocker()
        allowed = frozenset([Path('/tmp')])
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, allowed)
        blocker.check_access_allowed(Path('/etc/passwd'), FilesystemOperation.READ)

        blocker.reset()

        assert blocker.state == BlockerState.INACTIVE
        assert blocker.current_test_size is None
        assert blocker.current_enforcement_mode is None
        assert blocker.current_allowed_paths == frozenset()
        assert len(blocker.access_attempts) == 0
        assert len(blocker.warnings) == 0

    def it_resets_even_when_active(self) -> None:
        """Verify reset() works regardless of current state."""
        blocker = FakeFilesystemBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

        blocker.reset()

        assert blocker.state == BlockerState.INACTIVE

    def it_tracks_call_counts(self) -> None:
        """Verify the blocker tracks method invocation counts."""
        blocker = FakeFilesystemBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())
        blocker.check_access_allowed(Path('/path1'), FilesystemOperation.READ)
        blocker.check_access_allowed(Path('/path2'), FilesystemOperation.WRITE)
        blocker.deactivate()

        assert blocker.activate_count == 1
        assert blocker.deactivate_count == 1
        assert blocker.check_count == 2


@pytest.mark.small
class DescribeAllowedPathMatching:
    """Tests for allowed path matching logic."""

    def it_allows_exact_path_match(self) -> None:
        """Verify exact path matches are allowed."""
        allowed = frozenset([Path('/tmp/test.txt').resolve()])
        blocker = FakeFilesystemBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, allowed)

        assert blocker.check_access_allowed(Path('/tmp/test.txt'), FilesystemOperation.READ) is True

    def it_allows_child_paths(self) -> None:
        """Verify child paths under allowed directories are allowed."""
        allowed = frozenset([Path('/tmp').resolve()])
        blocker = FakeFilesystemBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, allowed)

        assert blocker.check_access_allowed(Path('/tmp/subdir/file.txt'), FilesystemOperation.WRITE) is True
        assert blocker.check_access_allowed(Path('/tmp/deep/nested/path/file'), FilesystemOperation.CREATE) is True

    def it_blocks_sibling_paths(self) -> None:
        """Verify sibling paths are blocked."""
        allowed = frozenset([Path('/tmp/allowed').resolve()])
        blocker = FakeFilesystemBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, allowed)

        assert blocker.check_access_allowed(Path('/tmp/other'), FilesystemOperation.READ) is False
        assert blocker.check_access_allowed(Path('/tmp'), FilesystemOperation.LIST) is False

    def it_blocks_parent_paths(self) -> None:
        """Verify parent paths are blocked."""
        allowed = frozenset([Path('/tmp/allowed/subdir').resolve()])
        blocker = FakeFilesystemBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, allowed)

        assert blocker.check_access_allowed(Path('/tmp/allowed'), FilesystemOperation.READ) is False
        assert blocker.check_access_allowed(Path('/tmp'), FilesystemOperation.LIST) is False

    def it_handles_multiple_allowed_paths(self) -> None:
        """Verify multiple allowed paths work correctly."""
        allowed = frozenset([Path('/tmp').resolve(), Path('/var/cache').resolve()])
        blocker = FakeFilesystemBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, allowed)

        assert blocker.check_access_allowed(Path('/tmp/file'), FilesystemOperation.READ) is True
        assert blocker.check_access_allowed(Path('/var/cache/data'), FilesystemOperation.WRITE) is True
        assert blocker.check_access_allowed(Path('/var/log/app.log'), FilesystemOperation.READ) is False


@pytest.mark.small
class DescribeFilesystemOperations:
    """Tests for different filesystem operation types."""

    @pytest.mark.parametrize(
        'operation',
        [
            FilesystemOperation.READ,
            FilesystemOperation.WRITE,
            FilesystemOperation.DELETE,
            FilesystemOperation.CREATE,
            FilesystemOperation.MODIFY,
            FilesystemOperation.STAT,
            FilesystemOperation.LIST,
        ],
    )
    def it_blocks_all_operation_types_for_small_tests(self, operation: FilesystemOperation) -> None:
        """Verify all operation types are blocked for small tests on non-allowed paths."""
        blocker = FakeFilesystemBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

        assert blocker.check_access_allowed(Path('/etc/passwd'), operation) is False

    @pytest.mark.parametrize(
        'operation',
        [
            FilesystemOperation.READ,
            FilesystemOperation.WRITE,
            FilesystemOperation.DELETE,
            FilesystemOperation.CREATE,
            FilesystemOperation.MODIFY,
            FilesystemOperation.STAT,
            FilesystemOperation.LIST,
        ],
    )
    def it_allows_all_operation_types_on_allowed_paths(self, operation: FilesystemOperation) -> None:
        """Verify all operation types are allowed on allowed paths."""
        allowed = frozenset([Path('/tmp').resolve()])
        blocker = FakeFilesystemBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, allowed)

        assert blocker.check_access_allowed(Path('/tmp/test'), operation) is True

    def it_treats_stat_operations_the_same_as_other_operations(self) -> None:
        """Verify STAT operations are blocked just like other operations (no special exemption)."""
        blocker = FakeFilesystemBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

        assert blocker.check_access_allowed(Path('/etc/passwd'), FilesystemOperation.STAT) is False
        assert blocker.check_access_allowed(Path('/home/user'), FilesystemOperation.LIST) is False


@pytest.mark.small
class DescribeFilesystemPatchingBlocker:
    """Tests for the FilesystemPatchingBlocker production adapter."""

    def it_starts_in_inactive_state(self) -> None:
        """Verify the blocker initializes in INACTIVE state."""
        blocker = FilesystemPatchingBlocker()

        assert blocker.state == BlockerState.INACTIVE

    def it_transitions_to_active_on_activate(self) -> None:
        """Verify activate() transitions from INACTIVE to ACTIVE."""
        blocker = FilesystemPatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

        assert blocker.state == BlockerState.ACTIVE

        blocker.deactivate()

    def it_transitions_to_inactive_on_deactivate(self) -> None:
        """Verify deactivate() transitions from ACTIVE to INACTIVE."""
        blocker = FilesystemPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

        blocker.deactivate()

        assert blocker.state == BlockerState.INACTIVE

    def it_fails_to_activate_when_already_active(self) -> None:
        """Verify activate() raises when already ACTIVE."""
        blocker = FilesystemPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

        try:
            with pytest.raises(ViolationError, match='INACTIVE'):
                blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())
        finally:
            blocker.reset()

    def it_fails_to_deactivate_when_inactive(self) -> None:
        """Verify deactivate() raises when already INACTIVE."""
        blocker = FilesystemPatchingBlocker()

        with pytest.raises(ViolationError, match='ACTIVE'):
            blocker.deactivate()

    def it_stores_activation_parameters(self) -> None:
        """Verify the blocker stores test size, enforcement mode, and allowed paths."""
        blocker = FilesystemPatchingBlocker()
        allowed = frozenset([Path('/tmp')])

        blocker.activate(TestSize.MEDIUM, EnforcementMode.WARN, allowed)

        assert blocker.current_test_size == TestSize.MEDIUM
        assert blocker.current_enforcement_mode == EnforcementMode.WARN
        assert blocker.current_allowed_paths == allowed

        blocker.deactivate()

    def it_blocks_all_access_for_small_tests(self) -> None:
        """Verify small tests cannot access any filesystem without allowed paths."""
        blocker = FilesystemPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

        assert blocker.check_access_allowed(Path('/etc/passwd'), FilesystemOperation.READ) is False
        assert blocker.check_access_allowed(Path('/home/user/file.txt'), FilesystemOperation.WRITE) is False

        blocker.deactivate()

    def it_allows_access_to_allowed_paths_for_small_tests(self) -> None:
        """Verify small tests can access allowed paths."""
        allowed = frozenset([Path('/tmp').resolve()])
        blocker = FilesystemPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, allowed)

        assert blocker.check_access_allowed(Path('/tmp/test.txt'), FilesystemOperation.WRITE) is True
        assert blocker.check_access_allowed(Path('/tmp/subdir/file.txt'), FilesystemOperation.READ) is True

        blocker.deactivate()

    def it_allows_all_access_for_medium_tests(self) -> None:
        """Verify medium tests can access any filesystem."""
        blocker = FilesystemPatchingBlocker()
        blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT, frozenset())

        assert blocker.check_access_allowed(Path('/etc/passwd'), FilesystemOperation.READ) is True
        assert blocker.check_access_allowed(Path('/home/user/file.txt'), FilesystemOperation.WRITE) is True

        blocker.deactivate()

    def it_allows_all_access_for_large_tests(self) -> None:
        """Verify large tests can access any filesystem."""
        blocker = FilesystemPatchingBlocker()
        blocker.activate(TestSize.LARGE, EnforcementMode.STRICT, frozenset())

        assert blocker.check_access_allowed(Path('/etc/passwd'), FilesystemOperation.READ) is True
        assert blocker.check_access_allowed(Path('/any/path'), FilesystemOperation.DELETE) is True

        blocker.deactivate()

    def it_raises_on_violation_in_strict_mode(self) -> None:
        """Verify on_violation raises FilesystemAccessViolationError in STRICT mode."""
        blocker = FilesystemPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

        with pytest.raises(FilesystemAccessViolationError) as exc_info:
            blocker.on_violation(Path('/etc/passwd'), FilesystemOperation.READ, 'test_module.py::test_fn')

        assert exc_info.value.path == Path('/etc/passwd')
        assert exc_info.value.operation == FilesystemOperation.READ

        blocker.deactivate()

    def it_resets_to_initial_state(self) -> None:
        """Verify reset() returns blocker to initial state."""
        blocker = FilesystemPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

        blocker.reset()

        assert blocker.state == BlockerState.INACTIVE
        assert blocker.current_test_size is None
        assert blocker.current_enforcement_mode is None
        assert blocker.current_allowed_paths == frozenset()

    def it_patches_builtins_open_on_activate(self) -> None:
        """Verify builtins.open is patched when activated."""
        import builtins

        original_open = builtins.open
        blocker = FilesystemPatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

        assert builtins.open is not original_open

        blocker.deactivate()

        assert builtins.open is original_open

    def it_restores_builtins_open_on_deactivate(self) -> None:
        """Verify builtins.open is restored when deactivated."""
        import builtins

        original_open = builtins.open
        blocker = FilesystemPatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())
        blocker.deactivate()

        assert builtins.open is original_open

    def it_restores_builtins_open_on_reset(self) -> None:
        """Verify builtins.open is restored on reset."""
        import builtins

        original_open = builtins.open
        blocker = FilesystemPatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())
        blocker.reset()

        assert builtins.open is original_open
