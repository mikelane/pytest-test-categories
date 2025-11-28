"""Integration tests for the filesystem blocker production adapter.

These tests verify that FilesystemPatchingBlocker correctly intercepts
real filesystem operations using actual file operations.

All tests use @pytest.mark.medium since they involve real filesystem operations
but do not require external resources.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from pytest_test_categories.adapters.filesystem import FilesystemPatchingBlocker
from pytest_test_categories.exceptions import FilesystemAccessViolationError
from pytest_test_categories.ports.network import EnforcementMode
from pytest_test_categories.types import TestSize

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.medium
class DescribeFilesystemPatchingBlockerIntegration:
    """Integration tests for FilesystemPatchingBlocker with real filesystem operations."""

    def it_blocks_real_file_read_for_small_test(self, tmp_path: Path) -> None:
        """Verify real open() for reading is blocked for small tests in STRICT mode."""
        blocker = FilesystemPatchingBlocker()
        test_file = tmp_path / 'outside_allowed' / 'test.txt'
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text('test content')

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            with pytest.raises(FilesystemAccessViolationError) as exc_info:
                open(test_file)  # noqa: SIM115, PTH123

            assert exc_info.value.test_size == TestSize.SMALL
            assert 'read' in str(exc_info.value.operation)

        finally:
            blocker.reset()

    def it_blocks_real_file_write_for_small_test(self, tmp_path: Path) -> None:
        """Verify real open() for writing is blocked for small tests in STRICT mode."""
        blocker = FilesystemPatchingBlocker()
        test_file = tmp_path / 'outside_allowed' / 'write_test.txt'
        test_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            with pytest.raises(FilesystemAccessViolationError) as exc_info:
                open(test_file, 'w')  # noqa: SIM115, PTH123

            assert exc_info.value.test_size == TestSize.SMALL
            assert 'write' in str(exc_info.value.operation)

        finally:
            blocker.reset()

    def it_allows_access_to_allowed_paths_for_small_test(self, tmp_path: Path) -> None:
        """Verify small tests can access files in allowed paths."""
        blocker = FilesystemPatchingBlocker()
        allowed_dir = tmp_path / 'allowed'
        allowed_dir.mkdir(parents=True, exist_ok=True)
        test_file = allowed_dir / 'test.txt'

        allowed_paths = frozenset([allowed_dir.resolve()])

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, allowed_paths)

            with open(test_file, 'w') as f:  # noqa: PTH123
                f.write('test content')

            with open(test_file) as f:  # noqa: PTH123
                content = f.read()

            assert content == 'test content'

        finally:
            blocker.reset()

    def it_blocks_access_outside_allowed_paths_for_small_test(self, tmp_path: Path) -> None:
        """Verify small tests cannot access files outside allowed paths."""
        blocker = FilesystemPatchingBlocker()
        allowed_dir = tmp_path / 'allowed'
        allowed_dir.mkdir(parents=True, exist_ok=True)
        outside_file = tmp_path / 'outside' / 'test.txt'
        outside_file.parent.mkdir(parents=True, exist_ok=True)

        allowed_paths = frozenset([allowed_dir.resolve()])

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, allowed_paths)

            with pytest.raises(FilesystemAccessViolationError):
                open(outside_file, 'w')  # noqa: SIM115, PTH123

        finally:
            blocker.reset()

    def it_allows_all_access_for_medium_test(self, tmp_path: Path) -> None:
        """Verify medium tests can access any filesystem path."""
        blocker = FilesystemPatchingBlocker()
        test_file = tmp_path / 'any_location' / 'test.txt'
        test_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT, frozenset())

            with open(test_file, 'w') as f:  # noqa: PTH123
                f.write('medium test content')

            with open(test_file) as f:  # noqa: PTH123
                content = f.read()

            assert content == 'medium test content'

        finally:
            blocker.reset()

    def it_allows_all_access_for_large_test(self, tmp_path: Path) -> None:
        """Verify large tests can access any filesystem path."""
        blocker = FilesystemPatchingBlocker()
        test_file = tmp_path / 'any_location' / 'test.txt'
        test_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            blocker.activate(TestSize.LARGE, EnforcementMode.STRICT, frozenset())

            with open(test_file, 'w') as f:  # noqa: PTH123
                f.write('large test content')

            with open(test_file) as f:  # noqa: PTH123
                content = f.read()

            assert content == 'large test content'

        finally:
            blocker.reset()

    def it_allows_access_in_warn_mode(self, tmp_path: Path) -> None:
        """Verify filesystem access proceeds in WARN mode (no exception raised)."""
        blocker = FilesystemPatchingBlocker()
        test_file = tmp_path / 'warn_mode' / 'test.txt'
        test_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.WARN, frozenset())

            with open(test_file, 'w') as f:  # noqa: PTH123
                f.write('warn mode content')

            with open(test_file) as f:  # noqa: PTH123
                content = f.read()

            assert content == 'warn mode content'

        finally:
            blocker.reset()

    def it_allows_access_in_off_mode(self, tmp_path: Path) -> None:
        """Verify filesystem access proceeds in OFF mode (no interception)."""
        blocker = FilesystemPatchingBlocker()
        test_file = tmp_path / 'off_mode' / 'test.txt'
        test_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.OFF, frozenset())

            with open(test_file, 'w') as f:  # noqa: PTH123
                f.write('off mode content')

            with open(test_file) as f:  # noqa: PTH123
                content = f.read()

            assert content == 'off mode content'

        finally:
            blocker.reset()

    def it_restores_open_after_deactivation(self, tmp_path: Path) -> None:
        """Verify open() is fully restored after deactivation."""
        import builtins

        original_open = builtins.open
        blocker = FilesystemPatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

        assert builtins.open is not original_open

        blocker.deactivate()

        assert builtins.open is original_open

        test_file = tmp_path / 'restored' / 'test.txt'
        test_file.parent.mkdir(parents=True, exist_ok=True)
        with open(test_file, 'w') as f:  # noqa: PTH123
            f.write('restored content')

        with open(test_file) as f:  # noqa: PTH123
            content = f.read()

        assert content == 'restored content'

    def it_handles_multiple_activate_deactivate_cycles(self, tmp_path: Path) -> None:
        """Verify blocker works correctly through multiple cycles."""
        import builtins

        original_open = builtins.open
        blocker = FilesystemPatchingBlocker()
        test_file = tmp_path / 'cycles' / 'test.txt'
        test_file.parent.mkdir(parents=True, exist_ok=True)

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())
        assert builtins.open is not original_open
        blocker.deactivate()
        assert builtins.open is original_open

        blocker.activate(TestSize.MEDIUM, EnforcementMode.WARN, frozenset())
        assert builtins.open is not original_open
        blocker.deactivate()
        assert builtins.open is original_open

        with open(test_file, 'w') as f:  # noqa: PTH123
            f.write('after cycles')

        with open(test_file) as f:  # noqa: PTH123
            content = f.read()

        assert content == 'after cycles'


@pytest.mark.medium
class DescribeFilesystemPatchingBlockerEdgeCases:
    """Integration tests for edge cases and error scenarios."""

    def it_handles_file_creation_with_x_mode(self, tmp_path: Path) -> None:
        """Verify file creation with 'x' mode is properly detected as CREATE operation."""
        blocker = FilesystemPatchingBlocker()
        test_file = tmp_path / 'create_mode' / 'new_file.txt'
        test_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            with pytest.raises(FilesystemAccessViolationError) as exc_info:
                open(test_file, 'x')  # noqa: SIM115, PTH123

            assert 'create' in str(exc_info.value.operation)

        finally:
            blocker.reset()

    def it_handles_append_mode(self, tmp_path: Path) -> None:
        """Verify append mode is properly detected as WRITE operation."""
        blocker = FilesystemPatchingBlocker()
        test_file = tmp_path / 'append_mode' / 'test.txt'
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text('initial content')

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            with pytest.raises(FilesystemAccessViolationError) as exc_info:
                open(test_file, 'a')  # noqa: SIM115, PTH123

            assert 'write' in str(exc_info.value.operation)

        finally:
            blocker.reset()

    def it_cleans_up_on_reset_even_if_active(self, tmp_path: Path) -> None:
        """Verify reset() properly cleans up even when blocker is active."""
        import builtins

        original_open = builtins.open
        blocker = FilesystemPatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

        blocker.reset()

        assert builtins.open is original_open

        test_file = tmp_path / 'reset_cleanup' / 'test.txt'
        test_file.parent.mkdir(parents=True, exist_ok=True)
        with open(test_file, 'w') as f:  # noqa: PTH123
            f.write('after reset')

    def it_preserves_open_functionality_for_allowed_paths(self, tmp_path: Path) -> None:
        """Verify open() functionality is preserved when access is allowed."""
        blocker = FilesystemPatchingBlocker()
        allowed_dir = tmp_path / 'preserved_functionality'
        allowed_dir.mkdir(parents=True, exist_ok=True)
        test_file = allowed_dir / 'test.txt'

        allowed_paths = frozenset([allowed_dir.resolve()])

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, allowed_paths)

            with open(test_file, 'w', encoding='utf-8', newline='\n') as f:  # noqa: PTH123
                f.write('line1\n')
                f.write('line2\n')

            with open(test_file, encoding='utf-8') as f:  # noqa: PTH123
                lines = f.readlines()

            assert lines == ['line1\n', 'line2\n']

        finally:
            blocker.reset()

    def it_handles_path_objects(self, tmp_path: Path) -> None:
        """Verify Path objects work correctly with the blocker."""
        blocker = FilesystemPatchingBlocker()
        test_file = tmp_path / 'path_object' / 'test.txt'
        test_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            with pytest.raises(FilesystemAccessViolationError):
                open(test_file, 'w')  # noqa: SIM115, PTH123

        finally:
            blocker.reset()

    def it_handles_string_paths(self, tmp_path: Path) -> None:
        """Verify string paths work correctly with the blocker."""
        blocker = FilesystemPatchingBlocker()
        test_file = tmp_path / 'string_path' / 'test.txt'
        test_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            with pytest.raises(FilesystemAccessViolationError):
                open(str(test_file), 'w')  # noqa: SIM115, PTH123

        finally:
            blocker.reset()
