"""Script to check that coverage hasn't decreased."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from pytest_test_categories.coverage.readers import CoveragePyReader
from tests._utils.file_system import (
    FileSystemPort,
    RealFileSystem,
)

if TYPE_CHECKING:
    from pytest_test_categories.types import CoverageReaderPort

COVERAGE_FILE = Path('.coverage')
MINIMUM_COVERAGE = 95.0
STORED_COVERAGE_FILE = Path('coverage_target.txt')


def get_current_coverage(coverage_reader: CoverageReaderPort) -> float:
    """Read the coverage percentage using the provided coverage reader.

    Args:
        coverage_reader: Port for reading coverage data.

    Returns:
        The total coverage percentage.

    """
    return coverage_reader.get_total_coverage()


def read_stored_coverage(fs: FileSystemPort) -> float:
    """Read the stored coverage target.

    Args:
        fs: File system port for reading the stored coverage file.

    Returns:
        The stored coverage target or minimum coverage if file does not exist.

    """
    if not fs.exists(STORED_COVERAGE_FILE):
        return MINIMUM_COVERAGE
    return float(fs.read_text(STORED_COVERAGE_FILE).strip())


def store_coverage(fs: FileSystemPort, coverage: float) -> None:
    """Store the current coverage as the new target.

    Args:
        fs: File system port for writing the coverage file.
        coverage: Coverage percentage to store.

    """
    fs.write_text(STORED_COVERAGE_FILE, f'{coverage}\n')


def main() -> int:
    """Check coverage and ensure it hasn't decreased."""
    # Create real adapters for production use
    fs = RealFileSystem()
    coverage_reader = CoveragePyReader()

    if not fs.exists(COVERAGE_FILE):
        print('No coverage data found. Run pytest --cov first.')
        return 1

    current_coverage = get_current_coverage(coverage_reader)
    stored_coverage = read_stored_coverage(fs)

    if current_coverage < stored_coverage:
        print(f'Coverage {current_coverage:.2f}% is below target {stored_coverage:.2f}%')
        return 1

    if current_coverage > stored_coverage:
        store_coverage(fs, current_coverage)
        print(f'Coverage increased to {current_coverage:.2f}%')
    else:
        print(f'Coverage steady at {current_coverage:.2f}%')

    return 0


if __name__ == '__main__':
    sys.exit(main())
