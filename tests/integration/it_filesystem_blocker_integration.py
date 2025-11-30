"""Integration tests for the filesystem blocker production adapter.

These tests verify that FilesystemPatchingBlocker correctly intercepts
real filesystem operations using actual file operations.

All tests use @pytest.mark.medium since they involve real filesystem operations
but do not require external resources.
"""

from __future__ import annotations

import builtins
import os
import shutil
from pathlib import Path

import pytest

from pytest_test_categories.adapters.filesystem import FilesystemPatchingBlocker
from pytest_test_categories.exceptions import FilesystemAccessViolationError
from pytest_test_categories.ports.network import EnforcementMode
from pytest_test_categories.types import TestSize


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


@pytest.mark.medium
class DescribePathBlocking:
    """Integration tests for blocking pathlib.Path operations."""

    def it_blocks_path_read_text_for_small_tests(self, tmp_path: Path) -> None:
        """Verify Path.read_text() is blocked for small tests."""
        blocker = FilesystemPatchingBlocker()
        test_file = tmp_path / 'pathlib_test' / 'read.txt'
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text('test content')

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            with pytest.raises(FilesystemAccessViolationError) as exc_info:
                Path(test_file).read_text()

            assert exc_info.value.test_size == TestSize.SMALL
            assert 'read' in str(exc_info.value.operation)

        finally:
            blocker.reset()

    def it_blocks_path_write_text_for_small_tests(self, tmp_path: Path) -> None:
        """Verify Path.write_text() is blocked for small tests."""
        blocker = FilesystemPatchingBlocker()
        test_file = tmp_path / 'pathlib_test' / 'write.txt'
        test_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            with pytest.raises(FilesystemAccessViolationError) as exc_info:
                Path(test_file).write_text('test')

            assert exc_info.value.test_size == TestSize.SMALL
            assert 'write' in str(exc_info.value.operation)

        finally:
            blocker.reset()

    def it_blocks_path_read_bytes_for_small_tests(self, tmp_path: Path) -> None:
        """Verify Path.read_bytes() is blocked for small tests."""
        blocker = FilesystemPatchingBlocker()
        test_file = tmp_path / 'pathlib_test' / 'bytes.txt'
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_bytes(b'test content')

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            with pytest.raises(FilesystemAccessViolationError) as exc_info:
                Path(test_file).read_bytes()

            assert exc_info.value.test_size == TestSize.SMALL
            assert 'read' in str(exc_info.value.operation)

        finally:
            blocker.reset()

    def it_blocks_path_write_bytes_for_small_tests(self, tmp_path: Path) -> None:
        """Verify Path.write_bytes() is blocked for small tests."""
        blocker = FilesystemPatchingBlocker()
        test_file = tmp_path / 'pathlib_test' / 'write_bytes.txt'
        test_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            with pytest.raises(FilesystemAccessViolationError) as exc_info:
                Path(test_file).write_bytes(b'test')

            assert exc_info.value.test_size == TestSize.SMALL
            assert 'write' in str(exc_info.value.operation)

        finally:
            blocker.reset()

    def it_blocks_path_unlink_for_small_tests(self, tmp_path: Path) -> None:
        """Verify Path.unlink() is blocked for small tests."""
        blocker = FilesystemPatchingBlocker()
        test_file = tmp_path / 'pathlib_test' / 'delete.txt'
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text('to delete')

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            with pytest.raises(FilesystemAccessViolationError) as exc_info:
                Path(test_file).unlink()

            assert exc_info.value.test_size == TestSize.SMALL
            assert 'delete' in str(exc_info.value.operation)

        finally:
            blocker.reset()

    def it_blocks_path_mkdir_for_small_tests(self, tmp_path: Path) -> None:
        """Verify Path.mkdir() is blocked for small tests."""
        blocker = FilesystemPatchingBlocker()
        test_dir = tmp_path / 'pathlib_test' / 'new_dir'
        test_dir.parent.mkdir(parents=True, exist_ok=True)

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            with pytest.raises(FilesystemAccessViolationError) as exc_info:
                Path(test_dir).mkdir()

            assert exc_info.value.test_size == TestSize.SMALL
            assert 'create' in str(exc_info.value.operation)

        finally:
            blocker.reset()

    def it_blocks_path_rmdir_for_small_tests(self, tmp_path: Path) -> None:
        """Verify Path.rmdir() is blocked for small tests."""
        blocker = FilesystemPatchingBlocker()
        test_dir = tmp_path / 'pathlib_test' / 'empty_dir'
        test_dir.mkdir(parents=True, exist_ok=True)

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            with pytest.raises(FilesystemAccessViolationError) as exc_info:
                Path(test_dir).rmdir()

            assert exc_info.value.test_size == TestSize.SMALL
            assert 'delete' in str(exc_info.value.operation)

        finally:
            blocker.reset()

    def it_blocks_path_rename_for_small_tests(self, tmp_path: Path) -> None:
        """Verify Path.rename() is blocked for small tests."""
        blocker = FilesystemPatchingBlocker()
        test_file = tmp_path / 'pathlib_test' / 'rename_source.txt'
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text('rename me')
        target = tmp_path / 'pathlib_test' / 'rename_target.txt'

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            with pytest.raises(FilesystemAccessViolationError) as exc_info:
                Path(test_file).rename(target)

            assert exc_info.value.test_size == TestSize.SMALL
            assert 'modify' in str(exc_info.value.operation)

        finally:
            blocker.reset()

    def it_blocks_path_open_for_small_tests(self, tmp_path: Path) -> None:
        """Verify Path.open() is blocked for small tests."""
        blocker = FilesystemPatchingBlocker()
        test_file = tmp_path / 'pathlib_test' / 'open_test.txt'
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text('test content')

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            with pytest.raises(FilesystemAccessViolationError):
                Path(test_file).open()  # noqa: SIM115

        finally:
            blocker.reset()

    def it_allows_pathlib_on_allowed_paths_for_small_tests(self, tmp_path: Path) -> None:
        """Verify pathlib operations are allowed on allowed paths for small tests."""
        blocker = FilesystemPatchingBlocker()
        allowed_dir = tmp_path / 'allowed_pathlib'
        allowed_dir.mkdir(parents=True, exist_ok=True)
        test_file = allowed_dir / 'test.txt'

        allowed_paths = frozenset([allowed_dir.resolve()])

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, allowed_paths)

            Path(test_file).write_text('allowed content')
            content = Path(test_file).read_text()

            assert content == 'allowed content'

        finally:
            blocker.reset()

    def it_allows_pathlib_for_medium_tests(self, tmp_path: Path) -> None:
        """Verify pathlib operations are allowed for medium tests."""
        blocker = FilesystemPatchingBlocker()
        test_file = tmp_path / 'medium_pathlib' / 'test.txt'
        test_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT, frozenset())

            Path(test_file).write_text('medium content')
            content = Path(test_file).read_text()

            assert content == 'medium content'

        finally:
            blocker.reset()


@pytest.mark.medium
class DescribeShutilBlocking:
    """Integration tests for blocking shutil operations."""

    def it_blocks_shutil_copy_for_small_tests(self, tmp_path: Path) -> None:
        """Verify shutil.copy() is blocked for small tests."""
        blocker = FilesystemPatchingBlocker()
        source = tmp_path / 'shutil_test' / 'source.txt'
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text('source content')
        dest = tmp_path / 'shutil_test' / 'dest.txt'

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            with pytest.raises(FilesystemAccessViolationError) as exc_info:
                shutil.copy(source, dest)

            assert exc_info.value.test_size == TestSize.SMALL

        finally:
            blocker.reset()

    def it_blocks_shutil_copy2_for_small_tests(self, tmp_path: Path) -> None:
        """Verify shutil.copy2() is blocked for small tests."""
        blocker = FilesystemPatchingBlocker()
        source = tmp_path / 'shutil_test' / 'source2.txt'
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text('source content')
        dest = tmp_path / 'shutil_test' / 'dest2.txt'

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            with pytest.raises(FilesystemAccessViolationError) as exc_info:
                shutil.copy2(source, dest)

            assert exc_info.value.test_size == TestSize.SMALL

        finally:
            blocker.reset()

    def it_blocks_shutil_copytree_for_small_tests(self, tmp_path: Path) -> None:
        """Verify shutil.copytree() is blocked for small tests."""
        blocker = FilesystemPatchingBlocker()
        source_dir = tmp_path / 'shutil_test' / 'source_dir'
        source_dir.mkdir(parents=True, exist_ok=True)
        (source_dir / 'file.txt').write_text('content')
        dest_dir = tmp_path / 'shutil_test' / 'dest_dir'

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            with pytest.raises(FilesystemAccessViolationError) as exc_info:
                shutil.copytree(source_dir, dest_dir)

            assert exc_info.value.test_size == TestSize.SMALL

        finally:
            blocker.reset()

    def it_blocks_shutil_move_for_small_tests(self, tmp_path: Path) -> None:
        """Verify shutil.move() is blocked for small tests."""
        blocker = FilesystemPatchingBlocker()
        source = tmp_path / 'shutil_test' / 'move_source.txt'
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text('move content')
        dest = tmp_path / 'shutil_test' / 'move_dest.txt'

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            with pytest.raises(FilesystemAccessViolationError) as exc_info:
                shutil.move(source, dest)

            assert exc_info.value.test_size == TestSize.SMALL

        finally:
            blocker.reset()

    def it_blocks_shutil_rmtree_for_small_tests(self, tmp_path: Path) -> None:
        """Verify shutil.rmtree() is blocked for small tests."""
        blocker = FilesystemPatchingBlocker()
        target_dir = tmp_path / 'shutil_test' / 'rmtree_target'
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / 'file.txt').write_text('content')

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            with pytest.raises(FilesystemAccessViolationError) as exc_info:
                shutil.rmtree(target_dir)

            assert exc_info.value.test_size == TestSize.SMALL
            assert 'delete' in str(exc_info.value.operation)

        finally:
            blocker.reset()

    def it_allows_shutil_on_allowed_paths_for_small_tests(self, tmp_path: Path) -> None:
        """Verify shutil operations are allowed on allowed paths for small tests."""
        blocker = FilesystemPatchingBlocker()
        allowed_dir = tmp_path / 'allowed_shutil'
        allowed_dir.mkdir(parents=True, exist_ok=True)
        source = allowed_dir / 'source.txt'
        source.write_text('source content')
        dest = allowed_dir / 'dest.txt'

        allowed_paths = frozenset([allowed_dir.resolve()])

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, allowed_paths)

            shutil.copy(source, dest)

            assert dest.read_text() == 'source content'

        finally:
            blocker.reset()

    def it_allows_shutil_for_medium_tests(self, tmp_path: Path) -> None:
        """Verify shutil operations are allowed for medium tests."""
        blocker = FilesystemPatchingBlocker()
        source = tmp_path / 'medium_shutil' / 'source.txt'
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text('source content')
        dest = tmp_path / 'medium_shutil' / 'dest.txt'

        try:
            blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT, frozenset())

            shutil.copy(source, dest)

            assert dest.read_text() == 'source content'

        finally:
            blocker.reset()


@pytest.mark.medium
class DescribeOsModuleBlocking:
    """Integration tests for blocking os module operations."""

    def it_blocks_os_remove_for_small_tests(self, tmp_path: Path) -> None:
        """Verify os.remove() is blocked for small tests."""
        blocker = FilesystemPatchingBlocker()
        test_file = tmp_path / 'os_test' / 'remove.txt'
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text('to remove')

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            with pytest.raises(FilesystemAccessViolationError) as exc_info:
                os.remove(test_file)  # noqa: PTH107

            assert exc_info.value.test_size == TestSize.SMALL
            assert 'delete' in str(exc_info.value.operation)

        finally:
            blocker.reset()

    def it_blocks_os_unlink_for_small_tests(self, tmp_path: Path) -> None:
        """Verify os.unlink() is blocked for small tests."""
        blocker = FilesystemPatchingBlocker()
        test_file = tmp_path / 'os_test' / 'unlink.txt'
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text('to unlink')

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            with pytest.raises(FilesystemAccessViolationError) as exc_info:
                os.unlink(test_file)  # noqa: PTH108

            assert exc_info.value.test_size == TestSize.SMALL
            assert 'delete' in str(exc_info.value.operation)

        finally:
            blocker.reset()

    def it_blocks_os_mkdir_for_small_tests(self, tmp_path: Path) -> None:
        """Verify os.mkdir() is blocked for small tests."""
        blocker = FilesystemPatchingBlocker()
        test_dir = tmp_path / 'os_test' / 'new_dir'
        test_dir.parent.mkdir(parents=True, exist_ok=True)

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            with pytest.raises(FilesystemAccessViolationError) as exc_info:
                os.mkdir(test_dir)  # noqa: PTH102

            assert exc_info.value.test_size == TestSize.SMALL
            assert 'create' in str(exc_info.value.operation)

        finally:
            blocker.reset()

    def it_blocks_os_makedirs_for_small_tests(self, tmp_path: Path) -> None:
        """Verify os.makedirs() is blocked for small tests."""
        blocker = FilesystemPatchingBlocker()
        test_dir = tmp_path / 'os_test' / 'deep' / 'nested' / 'dir'

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            with pytest.raises(FilesystemAccessViolationError) as exc_info:
                os.makedirs(test_dir)  # noqa: PTH103

            assert exc_info.value.test_size == TestSize.SMALL
            assert 'create' in str(exc_info.value.operation)

        finally:
            blocker.reset()

    def it_blocks_os_rmdir_for_small_tests(self, tmp_path: Path) -> None:
        """Verify os.rmdir() is blocked for small tests."""
        blocker = FilesystemPatchingBlocker()
        test_dir = tmp_path / 'os_test' / 'empty_dir'
        test_dir.mkdir(parents=True, exist_ok=True)

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            with pytest.raises(FilesystemAccessViolationError) as exc_info:
                os.rmdir(test_dir)  # noqa: PTH106

            assert exc_info.value.test_size == TestSize.SMALL
            assert 'delete' in str(exc_info.value.operation)

        finally:
            blocker.reset()

    def it_blocks_os_rename_for_small_tests(self, tmp_path: Path) -> None:
        """Verify os.rename() is blocked for small tests."""
        blocker = FilesystemPatchingBlocker()
        source = tmp_path / 'os_test' / 'rename_src.txt'
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text('rename me')
        dest = tmp_path / 'os_test' / 'rename_dst.txt'

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            with pytest.raises(FilesystemAccessViolationError) as exc_info:
                os.rename(source, dest)  # noqa: PTH104

            assert exc_info.value.test_size == TestSize.SMALL
            assert 'modify' in str(exc_info.value.operation)

        finally:
            blocker.reset()

    def it_blocks_os_replace_for_small_tests(self, tmp_path: Path) -> None:
        """Verify os.replace() is blocked for small tests."""
        blocker = FilesystemPatchingBlocker()
        source = tmp_path / 'os_test' / 'replace_src.txt'
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text('replace me')
        dest = tmp_path / 'os_test' / 'replace_dst.txt'

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())

            with pytest.raises(FilesystemAccessViolationError) as exc_info:
                os.replace(source, dest)  # noqa: PTH105

            assert exc_info.value.test_size == TestSize.SMALL
            assert 'modify' in str(exc_info.value.operation)

        finally:
            blocker.reset()

    def it_allows_os_operations_on_allowed_paths_for_small_tests(self, tmp_path: Path) -> None:
        """Verify os operations are allowed on allowed paths for small tests."""
        blocker = FilesystemPatchingBlocker()
        allowed_dir = tmp_path / 'allowed_os'
        allowed_dir.mkdir(parents=True, exist_ok=True)
        test_dir = allowed_dir / 'new_dir'

        allowed_paths = frozenset([allowed_dir.resolve()])

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, allowed_paths)

            os.mkdir(test_dir)  # noqa: PTH102

            assert test_dir.exists()

        finally:
            blocker.reset()

    def it_allows_os_operations_for_medium_tests(self, tmp_path: Path) -> None:
        """Verify os operations are allowed for medium tests."""
        blocker = FilesystemPatchingBlocker()
        test_dir = tmp_path / 'medium_os' / 'new_dir'
        test_dir.parent.mkdir(parents=True, exist_ok=True)

        try:
            blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT, frozenset())

            os.mkdir(test_dir)  # noqa: PTH102

            assert test_dir.exists()

        finally:
            blocker.reset()

    def it_allows_os_rename_on_allowed_paths_for_small_tests(self, tmp_path: Path) -> None:
        """Verify os.rename() is allowed on allowed paths for small tests."""
        blocker = FilesystemPatchingBlocker()
        allowed_dir = tmp_path / 'allowed_rename'
        allowed_dir.mkdir(parents=True, exist_ok=True)
        source = allowed_dir / 'source.txt'
        source.write_text('rename me')
        dest = allowed_dir / 'dest.txt'

        allowed_paths = frozenset([allowed_dir.resolve()])

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, allowed_paths)

            os.rename(source, dest)  # noqa: PTH104

            assert dest.exists()
            assert not source.exists()
            assert dest.read_text() == 'rename me'

        finally:
            blocker.reset()


@pytest.mark.medium
class DescribeShutilRmtreeCoverage:
    """Additional coverage tests for shutil.rmtree."""

    def it_allows_shutil_rmtree_for_medium_tests(self, tmp_path: Path) -> None:
        """Verify shutil.rmtree() is allowed for medium tests."""
        blocker = FilesystemPatchingBlocker()
        target_dir = tmp_path / 'to_delete'
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / 'file.txt').write_text('content')

        try:
            blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT, frozenset())

            shutil.rmtree(target_dir)

            assert not target_dir.exists()

        finally:
            blocker.reset()
