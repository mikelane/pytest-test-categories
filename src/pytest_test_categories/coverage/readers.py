"""Coverage reader adapters implementing the CoverageReaderPort interface."""

from __future__ import annotations

from io import StringIO

from coverage import Coverage
from coverage.exceptions import NoDataError
from pydantic import (
    BaseModel,
    Field,
)

from pytest_test_categories.types import CoverageReaderPort


class FakeCoverageReader(CoverageReaderPort, BaseModel):
    """Controllable coverage reader adapter for testing.

    This is a test double that allows tests to control coverage values explicitly
    rather than depending on actual coverage.py data. This eliminates dependencies
    on coverage files and makes tests deterministic.

    The FakeCoverageReader follows hexagonal architecture principles:
    - Implements the CoverageReaderPort interface
    - Provides controllable coverage values via constructor or property
    - Used in tests as a substitute for CoveragePyReader
    - Enables testing behavior without implementation details

    Example:
        >>> reader = FakeCoverageReader(coverage=85.5)
        >>> assert reader.get_total_coverage() == 85.5
        >>> reader.coverage = 100.0
        >>> assert reader.get_total_coverage() == 100.0

    """

    coverage: float = Field(0.0, description='Simulated coverage percentage (0.0 to 100.0)')

    def get_total_coverage(self) -> float:
        """Get the simulated coverage percentage.

        Returns:
            The simulated coverage percentage.

        """
        return self.coverage


class CoveragePyReader(CoverageReaderPort, BaseModel):
    """Production coverage reader that reads from coverage.py .coverage file.

    This is the production adapter that reads actual coverage data from
    coverage.py's data file. It uses the coverage.py API to load and
    report coverage statistics.

    The CoveragePyReader follows hexagonal architecture principles:
    - Implements the CoverageReaderPort interface
    - Reads from actual coverage.py data files
    - Used in production code
    - Provides real coverage statistics from test runs

    Example:
        >>> reader = CoveragePyReader()  # Uses default .coverage file
        >>> coverage = reader.get_total_coverage()
        >>> print(f"Total coverage: {coverage:.2f}%")

        >>> reader = CoveragePyReader(coverage_file='custom/.coverage')
        >>> coverage = reader.get_total_coverage()

    """

    coverage_file: str = Field('.coverage', description='Path to coverage.py data file')

    def get_total_coverage(self) -> float:
        """Get the total coverage percentage from coverage.py data file.

        Returns:
            The total coverage percentage (0.0 to 100.0).
            Returns 0.0 if the coverage file has no data.

        Raises:
            Exception: If the coverage file cannot be loaded.

        """
        cov = Coverage(data_file=self.coverage_file)
        cov.load()

        # Capture the coverage report output to extract the total percentage
        # coverage.report() returns the total coverage percentage
        output = StringIO()
        try:
            total_coverage = cov.report(file=output, show_missing=False)
        except NoDataError:
            # No data to report means 0% coverage
            return 0.0

        return total_coverage
