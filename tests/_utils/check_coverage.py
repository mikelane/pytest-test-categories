"""Script to check that coverage hasn't decreased."""

from __future__ import annotations

import sys
from pathlib import Path

from coverage import Coverage

COVERAGE_FILE = Path('.coverage')
MINIMUM_COVERAGE = 95.0
STORED_COVERAGE_FILE = Path('coverage_target.txt')


def read_coverage() -> float:
    """Read the coverage percentage from .coverage file."""
    cov = Coverage()
    cov.load()
    return cov.report(show_missing=True)


def read_stored_coverage() -> float:
    """Read the stored coverage target."""
    if not STORED_COVERAGE_FILE.exists():
        return MINIMUM_COVERAGE
    return float(STORED_COVERAGE_FILE.read_text().strip())


def store_coverage(coverage: float) -> None:
    """Store the current coverage as the new target."""
    STORED_COVERAGE_FILE.write_text(f'{coverage}\n')


def main() -> int:
    """Check coverage and ensure it hasn't decreased."""
    if not COVERAGE_FILE.exists():
        print('No coverage data found. Run pytest --cov first.')
        return 1

    current_coverage = read_coverage()
    stored_coverage = read_stored_coverage()

    if current_coverage < MINIMUM_COVERAGE:
        print(f'Coverage {current_coverage:.2f}% is below minimum {MINIMUM_COVERAGE}%')
        return 1

    if current_coverage < stored_coverage:
        print(f'Coverage has decreased from {stored_coverage:.2f}% to {current_coverage:.2f}%')
        return 1

    if current_coverage > stored_coverage:
        store_coverage(current_coverage)
        print(f'Coverage increased to {current_coverage:.2f}%')
    else:
        print(f'Coverage steady at {current_coverage:.2f}%')

    return 0


if __name__ == '__main__':
    sys.exit(main())
