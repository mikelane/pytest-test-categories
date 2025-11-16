"""Test edge cases for test size reporting functionality.

This module tests reporting scenarios that exercise all code paths,
including edge cases for detailed reports with failed unsized tests.
"""

from __future__ import annotations

import pytest


@pytest.mark.small
class DescribeReportEdgeCases:
    """Test edge cases in test size reporting."""

    def it_highlights_failed_unsized_tests_in_detailed_report(self, pytester: pytest.Pytester) -> None:
        """It highlights failed unsized tests with red color in detailed report.

        This test exercises line 157 in reporting.py which is the only uncovered line.
        Line 157 is the red highlighting for failed unsized tests.
        """
        # Given test files with failing unsized tests
        pytester.makepyfile(
            test_failing="""
            import pytest

            @pytest.mark.small
            def test_small_pass():
                assert True

            def test_unsized_fail():
                assert False, "Expected failure"
            """
        )

        # When we run pytest with detailed report flag
        result = pytester.runpytest('--test-size-report=detailed')

        # Then the detailed report should include the failed unsized test
        assert 'Detailed Test Size Report' in result.stdout.str()

        # And both tests should be present
        assert 'test_failing.py::test_small_pass' in result.stdout.str()
        assert 'test_failing.py::test_unsized_fail' in result.stdout.str()

        # And we should have both Pass and FAIL status
        assert 'Pass' in result.stdout.str()
        assert 'FAIL' in result.stdout.str()

        # And the unsized test should show in the report
        assert 'unsized' in result.stdout.str()
