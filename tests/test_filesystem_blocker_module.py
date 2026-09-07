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

import builtins
import types
from pathlib import Path

import pytest
from icontract import ViolationError

from pytest_test_categories.adapters import filesystem as filesystem_module
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

    def it_blocks_all_access_for_small_tests(self) -> None:
        """Verify small tests cannot access any filesystem - no exceptions."""
        blocker = FakeFilesystemBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

        assert blocker.check_access_allowed(Path('/etc/passwd'), FilesystemOperation.READ) is False
        assert blocker.check_access_allowed(Path('/home/user/file.txt'), FilesystemOperation.WRITE) is False
        assert blocker.check_access_allowed(Path('/tmp/test'), FilesystemOperation.CREATE) is False

    def it_blocks_all_access_for_small_tests_even_with_allowed_paths_argument(self) -> None:
        """Verify small tests block ALL filesystem access - allowed_paths is ignored.

        Note: The allowed_paths parameter still exists in the interface for backward
        compatibility, but it is ignored for small tests. This test verifies that
        small tests are fully hermetic with no escape hatches.
        """
        allowed = frozenset([Path('/tmp').resolve()])
        blocker = FakeFilesystemBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, allowed)

        # Even paths that would match allowed_paths are blocked for small tests
        assert blocker.check_access_allowed(Path('/tmp/test.txt'), FilesystemOperation.WRITE) is False
        assert blocker.check_access_allowed(Path('/tmp/subdir/file.txt'), FilesystemOperation.READ) is False
        assert blocker.check_access_allowed(Path('/etc/passwd'), FilesystemOperation.READ) is False

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
        # All paths are blocked for small tests (no tmp_path exception)
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

    def it_blocks_all_access_for_small_tests_even_with_allowed_paths(self) -> None:
        """Verify small tests block ALL filesystem - allowed_paths is ignored."""
        allowed = frozenset([Path('/tmp').resolve()])
        blocker = FilesystemPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, allowed)

        # Even paths in allowed_paths are blocked for small tests (no escape hatches)
        assert blocker.check_access_allowed(Path('/tmp/test.txt'), FilesystemOperation.WRITE) is False
        assert blocker.check_access_allowed(Path('/tmp/subdir/file.txt'), FilesystemOperation.READ) is False

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
        original_open = builtins.open
        blocker = FilesystemPatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

        assert builtins.open is not original_open

        blocker.deactivate()

        assert builtins.open is original_open

    def it_restores_builtins_open_on_deactivate(self) -> None:
        """Verify builtins.open is restored when deactivated."""
        original_open = builtins.open
        blocker = FilesystemPatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())
        blocker.deactivate()

        assert builtins.open is original_open

    def it_restores_builtins_open_on_reset(self) -> None:
        """Verify builtins.open is restored on reset."""
        original_open = builtins.open
        blocker = FilesystemPatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())
        blocker.reset()

        assert builtins.open is original_open


class _StandInFakePath:
    """Stand-in for pyfakefs's FakePath: a real class so patching it is harmless.

    Carries stub implementations of every attribute FilesystemPatchingBlocker
    patches, so that patching this stand-in succeeds identically to patching a
    real pathlib.Path, regardless of whether the fix under test is in place.
    """

    __module__ = 'pyfakefs.fake_pathlib'

    read_text = staticmethod(lambda *args, **kwargs: '')  # noqa: ARG005
    write_text = staticmethod(lambda *args, **kwargs: 0)  # noqa: ARG005
    read_bytes = staticmethod(lambda *args, **kwargs: b'')  # noqa: ARG005
    write_bytes = staticmethod(lambda *args, **kwargs: 0)  # noqa: ARG005
    open = staticmethod(lambda *args, **kwargs: None)  # noqa: ARG005
    unlink = staticmethod(lambda *args, **kwargs: None)  # noqa: ARG005
    mkdir = staticmethod(lambda *args, **kwargs: None)  # noqa: ARG005
    rmdir = staticmethod(lambda *args, **kwargs: None)  # noqa: ARG005
    rename = staticmethod(lambda *args, **kwargs: None)  # noqa: ARG005
    replace = staticmethod(lambda *args, **kwargs: None)  # noqa: ARG005


class _StandInFakePathlibModule:
    """Stand-in for pyfakefs's FakePathlibModule, exposing only `Path`."""

    Path = _StandInFakePath


@pytest.mark.medium
class DescribeFilesystemPatchingBlockerWithVirtualFilesystem:
    """Tests for FilesystemPatchingBlocker behavior when a virtual filesystem is active.

    Simulates pyfakefs having already rebound the adapter module's `pathlib` global to
    a fake pathlib module (the way pyfakefs replaces `pathlib` with
    `FakePathlibModule` in every already-imported module, including this adapter's
    own module). The blocker must treat this as evidence that a virtualizer already
    owns filesystem interception and must not install its own patches or report
    violations.

    Marked medium (not small) for the same reason as DescribeFakeFilesystemBlocker:
    the plugin's own filesystem enforcement only activates for @pytest.mark.small
    tests. If this class were small, the plugin's own blocker would patch the real
    pathlib.Path around these test bodies too, and monkeypatch's teardown of the
    `pathlib` global (which happens in pytest's teardown phase, after the plugin's
    own call-phase deactivation) would make the plugin's restore target the
    monkeypatched stand-in instead of the real class -- corrupting the real
    pathlib.Path for the rest of the test session. Running as medium sidesteps the
    outer enforcement entirely, matching how these tests already drive
    TestSize.SMALL explicitly through their own local blocker instances.
    """

    def it_skips_patching_builtins_open_when_virtual_filesystem_active(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify activation installs no patches when a virtual filesystem is active."""
        monkeypatch.setattr(filesystem_module, 'pathlib', _StandInFakePathlibModule())
        original_open = builtins.open
        original_read_text = _StandInFakePath.read_text
        blocker = FilesystemPatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

        assert builtins.open is original_open
        assert _StandInFakePath.read_text is original_read_text

        blocker.deactivate()

        assert builtins.open is original_open
        assert _StandInFakePath.read_text is original_read_text

    def it_allows_access_for_small_tests_when_virtual_filesystem_active(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify small tests are allowed filesystem access when pyfakefs is active."""
        monkeypatch.setattr(filesystem_module, 'pathlib', _StandInFakePathlibModule())
        blocker = FilesystemPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

        assert blocker.check_access_allowed(Path('/etc/passwd'), FilesystemOperation.READ) is True

        blocker.deactivate()

    def it_still_blocks_access_for_small_tests_when_no_virtual_filesystem_active(self) -> None:
        """Verify small tests remain blocked when no virtual filesystem is active."""
        blocker = FilesystemPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

        assert blocker.check_access_allowed(Path('/etc/passwd'), FilesystemOperation.READ) is False

        blocker.deactivate()

    def it_allows_access_when_builtins_open_has_been_replaced(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify a foreign builtins.open (pathlib/os/shutil untouched) is detected."""

        def foreign_open(*args: object, **kwargs: object) -> None:  # noqa: ARG001
            return None

        monkeypatch.setattr(builtins, 'open', foreign_open)
        blocker = FilesystemPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

        assert blocker.check_access_allowed(Path('/etc/passwd'), FilesystemOperation.READ) is True

        blocker.deactivate()

    def it_allows_access_when_os_has_been_replaced_with_a_non_module(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify a non-module `os` global (pathlib/open untouched) is detected."""
        monkeypatch.setattr(filesystem_module, 'os', object())
        blocker = FilesystemPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

        assert blocker.check_access_allowed(Path('/etc/passwd'), FilesystemOperation.READ) is True

        blocker.deactivate()

    def it_allows_access_when_shutil_has_been_replaced_with_a_non_module(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify a non-module `shutil` global (pathlib/os/open untouched) is detected."""
        monkeypatch.setattr(filesystem_module, 'shutil', object())
        blocker = FilesystemPatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

        assert blocker.check_access_allowed(Path('/etc/passwd'), FilesystemOperation.READ) is True

        blocker.deactivate()

    @pytest.mark.xfail(
        reason=(
            'Known gap tracked in issue #258: any exception raised inside _do_activate strands '
            'already-installed patches (builtins.open, pathlib.Path methods) with no recovery '
            'through the public API, because activate() only sets state = ACTIVE after '
            '_do_activate returns and deactivate() requires state == ACTIVE. Pre-existing '
            'fragility, not introduced by the #254 fix.'
        ),
        strict=True,
    )
    def it_does_not_leak_patched_builtins_open_when_activation_fails_partway_through(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """BUG (issue #254 follow-up).

        A bare `types.ModuleType` satisfies
        `isinstance(os, ModuleType)` -- the only check `_virtual_filesystem_is_active()`
        performs on `os` -- even though it has none of the real `os` module's
        functions. This lets a stand-in that merely LOOKS like a module (but
        is not pyfakefs's FakeOsModule, and provides none of `os.remove`,
        `os.mkdir`, etc.) sail past virtualizer detection.

        `_do_activate` therefore proceeds: it successfully patches
        `builtins.open` and every `pathlib.Path` method, then crashes with
        `AttributeError` inside `_patch_os_functions` (no `.remove` on the bare
        module). Because this happens inside `_do_activate`, which the base
        class's `activate()` calls BEFORE setting `self.state = ACTIVE`, the
        blocker's state never transitions to ACTIVE. `deactivate()` requires
        `state == ACTIVE` (icontract precondition), so nothing can restore the
        already-patched `builtins.open` / `pathlib.Path` through the normal
        deactivation path -- they stay corrupted.

        Note: this exact trigger (a bare `types.ModuleType` standing in for
        `os`) requires a deliberate monkeypatch -- no real tool used by this
        project's test suite produces that shape (pyfakefs's own `os`
        stand-in is `FakeOsModule`, which passes `isinstance(..., ModuleType)`
        fine, see `it_allows_access_when_os_has_been_replaced_with_a_non_module`
        above for the actually-reachable non-module case). The underlying
        fragility this proves -- ANY exception raised inside `_do_activate`
        leaves already-installed patches stranded with no recovery through
        the public API, because `FilesystemBlockerPort.activate()` only sets
        `state = ACTIVE` after `_do_activate` returns, and `deactivate()`
        requires `state == ACTIVE` -- predates this PR's diff (the pre-fix
        `_do_activate` had no virtualizer guard at all and would strand
        patches identically on any mid-patch exception).
        """
        original_open = builtins.open

        broken_os = types.ModuleType('broken_os')  # passes isinstance(os, ModuleType), has no os functions
        monkeypatch.setattr(filesystem_module, 'os', broken_os)

        blocker = FilesystemPatchingBlocker()

        try:
            with pytest.raises(AttributeError):
                blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            assert builtins.open is original_open
        finally:
            # Recovery has to bypass deactivate()'s ACTIVE precondition entirely.
            blocker.reset()
