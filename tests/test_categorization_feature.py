"""Test the categorization of tests by size."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(autouse=True)
def conftest_file(pytester: pytest.Pytester) -> Path:
    """Create a conftest file with the test categories plugin registered."""
    return pytester.makeconftest("""
        from pytest_test_categories.plugin import TestCategories

        def pytest_configure(config):
            config.pluginmanager.register(TestCategories())
    """)


@pytest.fixture
def minimal_test_file(pytester: pytest.Pytester, request: pytest.FixtureRequest) -> Path:
    """Create a test file with a single test marked with the specified size."""
    test_size = request.param

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

    def it_raises_error_when_test_has_multiple_size_markers(self, pytester: pytest.Pytester) -> None:
        test_file = pytester.makepyfile(
            test_file="""
            import pytest

            @pytest.mark.small
            @pytest.mark.medium
            def test_example():
                assert True
            """,
        )

        result: pytest.RunResult = pytester.runpytest(test_file)

        assert result.ret != 0

        result.stderr.fnmatch_lines(
            [
                '*Test cannot have multiple size markers: small, medium*',
            ]
        )
