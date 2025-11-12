"""Tests for check_coverage module using fake adapters."""

from __future__ import annotations

import pytest

from pytest_test_categories.coverage.readers import FakeCoverageReader
from tests._utils.check_coverage import (
    COVERAGE_FILE,
    MINIMUM_COVERAGE,
    STORED_COVERAGE_FILE,
    get_current_coverage,
    main,
    read_stored_coverage,
    store_coverage,
)
from tests._utils.file_system import FakeFileSystem


@pytest.mark.small
class DescribeReadStoredCoverage:
    """Tests for read_stored_coverage function."""

    def it_returns_minimum_coverage_when_file_does_not_exist(self) -> None:
        """Return minimum coverage when stored coverage file does not exist."""
        fs = FakeFileSystem()

        result = read_stored_coverage(fs)

        assert result == MINIMUM_COVERAGE

    def it_reads_coverage_value_from_stored_file(self) -> None:
        """Read the coverage value from the stored coverage file."""
        fs = FakeFileSystem()
        fs.write_text(STORED_COVERAGE_FILE, '98.5\n')

        result = read_stored_coverage(fs)

        assert result == 98.5

    def it_strips_whitespace_from_stored_value(self) -> None:
        """Strip whitespace from the stored coverage value."""
        fs = FakeFileSystem()
        fs.write_text(STORED_COVERAGE_FILE, '  97.3  \n')

        result = read_stored_coverage(fs)

        assert result == 97.3


@pytest.mark.small
class DescribeStoreCoverage:
    """Tests for store_coverage function."""

    def it_writes_coverage_value_to_file(self) -> None:
        """Write the coverage value to the stored coverage file."""
        fs = FakeFileSystem()

        store_coverage(fs, 99.2)

        content = fs.read_text(STORED_COVERAGE_FILE)
        assert content == '99.2\n'

    def it_overwrites_existing_coverage_value(self) -> None:
        """Overwrite existing coverage value in the file."""
        fs = FakeFileSystem()
        fs.write_text(STORED_COVERAGE_FILE, '85.0\n')

        store_coverage(fs, 92.1)

        content = fs.read_text(STORED_COVERAGE_FILE)
        assert content == '92.1\n'


@pytest.mark.small
class DescribeGetCurrentCoverage:
    """Tests for get_current_coverage function."""

    def it_returns_coverage_from_reader(self) -> None:
        """Return the coverage percentage from the coverage reader."""
        coverage_reader = FakeCoverageReader(coverage=87.5)

        result = get_current_coverage(coverage_reader)

        assert result == 87.5

    def it_handles_zero_coverage(self) -> None:
        """Handle zero coverage correctly."""
        coverage_reader = FakeCoverageReader(coverage=0.0)

        result = get_current_coverage(coverage_reader)

        assert result == 0.0

    def it_handles_full_coverage(self) -> None:
        """Handle 100% coverage correctly."""
        coverage_reader = FakeCoverageReader(coverage=100.0)

        result = get_current_coverage(coverage_reader)

        assert result == 100.0


@pytest.mark.small
class DescribeMain:
    """Tests for main function."""

    def it_returns_error_when_coverage_file_missing(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        """Return error code when coverage file does not exist."""
        fs = FakeFileSystem()
        coverage_reader = FakeCoverageReader(coverage=95.0)

        # Patch to use fake adapters
        from tests._utils import check_coverage

        monkeypatch.setattr(check_coverage, 'RealFileSystem', lambda: fs)
        monkeypatch.setattr(check_coverage, 'CoveragePyReader', lambda: coverage_reader)

        result = main()

        assert result == 1
        captured = capsys.readouterr()
        assert 'No coverage data found' in captured.out

    def it_returns_error_when_coverage_decreased(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        """Return error code when coverage decreased below target."""
        fs = FakeFileSystem()
        fs.write_text(COVERAGE_FILE, '')  # Coverage file exists
        fs.write_text(STORED_COVERAGE_FILE, '95.0\n')
        coverage_reader = FakeCoverageReader(coverage=90.0)

        # Patch to use fake adapters
        from tests._utils import check_coverage

        monkeypatch.setattr(check_coverage, 'RealFileSystem', lambda: fs)
        monkeypatch.setattr(check_coverage, 'CoveragePyReader', lambda: coverage_reader)

        result = main()

        assert result == 1
        captured = capsys.readouterr()
        assert 'Coverage 90.00% is below target 95.00%' in captured.out

    def it_returns_success_and_updates_when_coverage_increased(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        """Return success and update stored coverage when coverage increased."""
        fs = FakeFileSystem()
        fs.write_text(COVERAGE_FILE, '')  # Coverage file exists
        fs.write_text(STORED_COVERAGE_FILE, '90.0\n')
        coverage_reader = FakeCoverageReader(coverage=95.5)

        # Patch to use fake adapters
        from tests._utils import check_coverage

        monkeypatch.setattr(check_coverage, 'RealFileSystem', lambda: fs)
        monkeypatch.setattr(check_coverage, 'CoveragePyReader', lambda: coverage_reader)

        result = main()

        assert result == 0
        captured = capsys.readouterr()
        assert 'Coverage increased to 95.50%' in captured.out
        # Verify stored coverage was updated
        assert fs.read_text(STORED_COVERAGE_FILE) == '95.5\n'

    def it_returns_success_when_coverage_unchanged(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        """Return success when coverage is unchanged."""
        fs = FakeFileSystem()
        fs.write_text(COVERAGE_FILE, '')  # Coverage file exists
        fs.write_text(STORED_COVERAGE_FILE, '92.0\n')
        coverage_reader = FakeCoverageReader(coverage=92.0)

        # Patch to use fake adapters
        from tests._utils import check_coverage

        monkeypatch.setattr(check_coverage, 'RealFileSystem', lambda: fs)
        monkeypatch.setattr(check_coverage, 'CoveragePyReader', lambda: coverage_reader)

        result = main()

        assert result == 0
        captured = capsys.readouterr()
        assert 'Coverage steady at 92.00%' in captured.out
        # Verify stored coverage was NOT updated
        assert fs.read_text(STORED_COVERAGE_FILE) == '92.0\n'

    def it_uses_minimum_coverage_when_no_stored_target(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        """Use minimum coverage as target when stored coverage file does not exist."""
        fs = FakeFileSystem()
        fs.write_text(COVERAGE_FILE, '')  # Coverage file exists
        coverage_reader = FakeCoverageReader(coverage=96.0)

        # Patch to use fake adapters
        from tests._utils import check_coverage

        monkeypatch.setattr(check_coverage, 'RealFileSystem', lambda: fs)
        monkeypatch.setattr(check_coverage, 'CoveragePyReader', lambda: coverage_reader)

        result = main()

        assert result == 0
        captured = capsys.readouterr()
        assert 'Coverage increased to 96.00%' in captured.out
        # Verify new target was stored
        assert fs.read_text(STORED_COVERAGE_FILE) == '96.0\n'
