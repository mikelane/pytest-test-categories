"""Feature tests for coverage.py data file exclusion from database hermeticity.

coverage.py stores coverage data in sqlite3 databases:
  - .coverage              (default)
  - .coverage.<host>.<pid>.<suffix>  (with dynamic_context = test_function)

These files must not trigger DatabaseViolationError for small tests even
when --test-categories-enforcement=strict is active.

Each test varies the filename or expected outcome so that neither a
'return True' nor a 'return False' implementation can pass the class.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.medium


@pytest.fixture(autouse=True)
def conftest_file(pytester: pytest.Pytester) -> None:
    """Create a minimal conftest so the plugin is loaded."""
    pytester.makeconftest("""
        import pytest
    """)


class DescribeCoverageDataFileExclusionIntegration:
    """Integration tests: coverage data files pass through sqlite3 blocker in strict mode."""

    def it_allows_small_test_to_open_coverage_data_file_in_strict_mode(
        self,
        pytester: pytest.Pytester,
    ) -> None:
        """Small test opening a .coverage.host.pid.suffix file passes in strict mode."""
        pytester.makepyfile(
            test_coverage_suffixed="""
            import os
            import pytest
            import sqlite3

            @pytest.mark.small
            def test_opens_coverage_suffixed_file():
                path = os.path.join(os.getcwd(), '.coverage.testhost.12345.abcdef')
                conn = sqlite3.connect(path)
                conn.close()
            """
        )

        result = pytester.runpytest('-v', '--test-categories-enforcement=strict')

        result.assert_outcomes(passed=1)

    def it_allows_small_test_to_open_default_coverage_file_in_strict_mode(
        self,
        pytester: pytest.Pytester,
    ) -> None:
        """Small test opening the bare '.coverage' file passes in strict mode."""
        pytester.makepyfile(
            test_coverage_default="""
            import os
            import pytest
            import sqlite3

            @pytest.mark.small
            def test_opens_default_coverage_file():
                path = os.path.join(os.getcwd(), '.coverage')
                conn = sqlite3.connect(path)
                conn.close()
            """
        )

        result = pytester.runpytest('-v', '--test-categories-enforcement=strict')

        result.assert_outcomes(passed=1)

    def it_still_blocks_small_test_regular_sqlite_in_strict_mode(
        self,
        pytester: pytest.Pytester,
    ) -> None:
        """Small test opening a regular .db file still fails in strict mode."""
        pytester.makepyfile(
            test_regular_sqlite="""
            import os
            import pytest
            import sqlite3

            @pytest.mark.small
            def test_opens_regular_db():
                path = os.path.join(os.getcwd(), 'test.db')
                conn = sqlite3.connect(path)
                conn.close()
            """
        )

        result = pytester.runpytest('-v', '--test-categories-enforcement=strict')

        result.assert_outcomes(failed=1)
