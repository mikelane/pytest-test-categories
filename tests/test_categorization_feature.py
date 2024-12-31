"""Test the categorization of tests by size."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def minimal_test_file(pytester: pytest.Pytester, request: pytest.FixtureRequest) -> Path:
    """Create a test file with a single test marked with the specified size."""
    test_size = request.param

    pytester.makeconftest("""
        from pytest_test_categories.plugin import TestCategories

        def pytest_configure(config):
            config.pluginmanager.register(TestCategories())
    """)

    return pytester.makepyfile(
        test_file=f"""
        import pytest

        @pytest.mark.{test_size.lower()}
        def test_example():
            assert True
        """,
    )


class DescribeTestCategorization:
    @pytest.mark.parametrize(
        ('minimal_test_file', 'expected_label'),
        [
            pytest.param('small', '[SMALL]', id='small_test'),
            pytest.param('medium', '[MEDIUM]', id='medium_test'),
            pytest.param('large', '[LARGE]', id='large_test'),
            pytest.param('xlarge', '[XLARGE]', id='xlarge_test'),
        ],
        indirect=['minimal_test_file'],
    )
    def it_recognizes_test_size_when_marked_with_size_marker(
        self,
        pytester: pytest.Pytester,
        minimal_test_file: Path,
        expected_label: str,
    ) -> None:
        """Verify that tests are properly categorized in the output based on their size marker."""
        result: pytest.RunResult = pytester.runpytest('-vv', minimal_test_file)

        stdout = result.stdout.str()
        test_output_line = next(line for line in stdout.splitlines() if 'test_example' in line and 'PASSED' in line)
        assert (
            expected_label in test_output_line
        ), f'Test output should show size category {expected_label} next to test name'
