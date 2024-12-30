"""Test the categorization of tests by size."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def minimal_test_file(pytester: pytest.Pytester) -> None:
    """Create a test file with a single test marked as small."""
    pytester.makeconftest("""
        from pytest_test_categories.plugin import TestCategories

        def pytest_configure(config):
            config.pluginmanager.register(TestCategories())
    """)

    pytester.makepyfile(
        test_file="""
        import pytest

        @pytest.mark.small
        def test_example():
            assert True
        """,
    )


class DescribeTestCategorization:
    def it_recognizes_a_small_test_when_marked_with_small_marker(self, pytester: pytest.Pytester) -> None:
        result: pytest.RunResult = pytester.runpytest('-vv', 'test_file.py')

        stdout = result.stdout.str()
        test_output_line = next(line for line in stdout.splitlines() if 'test_example' in line and 'PASSED' in line)
        assert '[SMALL]' in test_output_line, 'Test output should show size category next to test name'
