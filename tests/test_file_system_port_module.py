"""Test the file system port and adapters for testing infrastructure.

This module tests the FileSystemPort interface and its adapters:
- FakeFileSystem: In-memory file system for fast, deterministic testing
- RealFileSystem: Production adapter that delegates to pathlib.Path

The file system follows hexagonal architecture pattern where:
- FileSystemPort is the Port (interface)
- FakeFileSystem is a Test Adapter (test double)
- RealFileSystem is a Production Adapter (real implementation)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests._utils.file_system import (
    FakeFileSystem,
    RealFileSystem,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.small
class DescribeFakeFileSystem:
    """Tests for the FakeFileSystem test double."""

    def it_reads_file_content_that_was_written(self) -> None:
        """Verify that FakeFileSystem can store and retrieve file content."""
        fs = FakeFileSystem()
        file_path = '/test/file.txt'
        content = 'Hello, World!'

        fs.write_text(file_path, content)
        retrieved_content = fs.read_text(file_path)

        assert retrieved_content == content

    def it_reports_file_exists_after_writing(self) -> None:
        """Verify that exists() returns True for files that were written."""
        fs = FakeFileSystem()
        file_path = '/test/file.txt'

        assert not fs.exists(file_path), 'File should not exist initially'

        fs.write_text(file_path, 'content')

        assert fs.exists(file_path), 'File should exist after writing'

    def it_reports_file_does_not_exist_initially(self) -> None:
        """Verify that exists() returns False for files that were never written."""
        fs = FakeFileSystem()

        assert not fs.exists('/nonexistent/file.txt')

    def it_raises_file_not_found_when_reading_nonexistent_file(self) -> None:
        """Verify that read_text() raises FileNotFoundError for missing files."""
        fs = FakeFileSystem()

        with pytest.raises(FileNotFoundError):
            fs.read_text('/nonexistent/file.txt')

    def it_overwrites_existing_content_when_writing_same_path(self) -> None:
        """Verify that writing to the same path replaces old content."""
        fs = FakeFileSystem()
        file_path = '/test/file.txt'

        fs.write_text(file_path, 'original content')
        fs.write_text(file_path, 'new content')

        assert fs.read_text(file_path) == 'new content'

    def it_handles_empty_file_content(self) -> None:
        """Verify that FakeFileSystem can store and retrieve empty strings."""
        fs = FakeFileSystem()
        file_path = '/test/empty.txt'

        fs.write_text(file_path, '')

        assert fs.exists(file_path)
        assert fs.read_text(file_path) == ''

    def it_supports_multiple_independent_files(self) -> None:
        """Verify that multiple files can exist independently in the fake filesystem."""
        fs = FakeFileSystem()
        files = {
            '/test/file1.txt': 'content 1',
            '/test/file2.txt': 'content 2',
            '/other/file3.txt': 'content 3',
        }

        for path, content in files.items():
            fs.write_text(path, content)

        for path, expected_content in files.items():
            assert fs.exists(path)
            assert fs.read_text(path) == expected_content

    def it_provides_helper_to_set_file_content(self) -> None:
        """Verify that set_file() helper works the same as write_text()."""
        fs = FakeFileSystem()
        file_path = '/test/file.txt'
        content = 'test content'

        fs.set_file(file_path, content)

        assert fs.exists(file_path)
        assert fs.read_text(file_path) == content

    def it_provides_helper_to_get_file_content(self) -> None:
        """Verify that get_file() helper works the same as read_text()."""
        fs = FakeFileSystem()
        file_path = '/test/file.txt'
        content = 'test content'

        fs.write_text(file_path, content)

        assert fs.get_file(file_path) == content


@pytest.mark.medium
class DescribeRealFileSystem:
    """Integration tests for the RealFileSystem adapter using real file I/O."""

    def it_reads_real_file_content(self, tmp_path: Path) -> None:
        """Verify that RealFileSystem reads actual file content from disk."""
        fs = RealFileSystem()
        test_file = tmp_path / 'test.txt'
        content = 'Real file content'
        test_file.write_text(content)

        retrieved_content = fs.read_text(test_file)

        assert retrieved_content == content

    def it_writes_real_file_content(self, tmp_path: Path) -> None:
        """Verify that RealFileSystem writes actual files to disk."""
        fs = RealFileSystem()
        test_file = tmp_path / 'output.txt'
        content = 'Written content'

        fs.write_text(test_file, content)

        assert test_file.exists()
        assert test_file.read_text() == content

    def it_reports_real_file_exists(self, tmp_path: Path) -> None:
        """Verify that exists() works with actual filesystem."""
        fs = RealFileSystem()
        test_file = tmp_path / 'test.txt'

        assert not fs.exists(test_file), 'File should not exist initially'

        test_file.write_text('content')

        assert fs.exists(test_file), 'File should exist after creation'

    def it_raises_file_not_found_for_missing_real_file(self, tmp_path: Path) -> None:
        """Verify that reading nonexistent real file raises FileNotFoundError."""
        fs = RealFileSystem()
        nonexistent_file = tmp_path / 'nonexistent.txt'

        with pytest.raises(FileNotFoundError):
            fs.read_text(nonexistent_file)

    def it_accepts_string_paths(self, tmp_path: Path) -> None:
        """Verify that RealFileSystem accepts string paths as well as Path objects."""
        fs = RealFileSystem()
        test_file = tmp_path / 'test.txt'
        content = 'String path test'

        # Use string path
        fs.write_text(str(test_file), content)

        assert test_file.exists()
        assert fs.read_text(str(test_file)) == content
