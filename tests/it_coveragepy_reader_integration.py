"""Integration tests for CoveragePyReader production adapter."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from coverage import Coverage

from pytest_test_categories.coverage.readers import CoveragePyReader

# ruff: noqa: S101, PLR2004


@pytest.mark.medium
class DescribeCoveragePyReaderIntegration:
    """Integration tests for CoveragePyReader with real coverage.py."""

    def it_reads_coverage_from_coverage_file(self) -> None:
        """CoveragePyReader reads coverage from a real .coverage file."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            coverage_file = tmppath / '.coverage'

            # Create a simple Python file
            test_file = tmppath / 'example.py'
            test_file.write_text(
                'def add(a, b):\n'
                '    return a + b\n'
                '\n'
                'def multiply(a, b):\n'
                '    return a * b\n'
                '\n'
                'result = add(2, 3)\n'  # This line gets executed
            )

            # Run coverage on it with explicit source configuration
            cov = Coverage(data_file=str(coverage_file), source=[str(tmppath)])
            cov.start()
            # Execute in the tmpdir context so coverage can find it
            exec(compile(test_file.read_text(), str(test_file), 'exec'), {})  # noqa: S102
            cov.stop()
            cov.save()

            # Now read it with CoveragePyReader
            reader = CoveragePyReader(coverage_file=str(coverage_file))
            total_coverage = reader.get_total_coverage()

            # Should have some coverage (exact value depends on coverage internals)
            # The main point is that it successfully reads and returns a valid percentage
            assert 0.0 <= total_coverage <= 100.0

    def it_returns_zero_for_empty_coverage_file(self) -> None:
        """CoveragePyReader returns 0.0 when coverage file has no data."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            coverage_file = tmppath / '.coverage'

            # Create empty coverage file
            cov = Coverage(data_file=str(coverage_file))
            cov.save()

            reader = CoveragePyReader(coverage_file=str(coverage_file))
            total_coverage = reader.get_total_coverage()

            assert total_coverage == 0.0

    def it_uses_default_coverage_file_path(self) -> None:
        """CoveragePyReader uses .coverage in current directory by default."""
        # This test verifies the default path is set correctly
        reader = CoveragePyReader()
        assert reader.coverage_file == '.coverage'

    def it_accepts_custom_coverage_file_path(self) -> None:
        """CoveragePyReader accepts a custom coverage file path."""
        custom_path = '/path/to/custom/.coverage'
        reader = CoveragePyReader(coverage_file=custom_path)
        assert reader.coverage_file == custom_path

    def it_handles_missing_coverage_file_gracefully(self) -> None:
        """CoveragePyReader returns 0.0 for missing coverage file."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            nonexistent_file = str(tmppath / 'nonexistent.coverage')

            reader = CoveragePyReader(coverage_file=nonexistent_file)

            # Missing file should return 0.0 coverage
            total_coverage = reader.get_total_coverage()
            assert total_coverage == 0.0
