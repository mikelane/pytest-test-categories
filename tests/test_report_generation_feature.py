"""Test generation of test size reports."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest


class DescribeTestSizeReporting:
    def it_generates_basic_console_report(self, pytester: pytest.Pytester) -> None:
        """Verify basic report generation with the --test-size-report flag."""
        # Given test files with various sized and unsized tests
        pytester.makepyfile(
            test_sized="""
            import pytest

            @pytest.mark.small
            def test_small():
                assert True

            @pytest.mark.medium
            def test_medium():
                assert True

            @pytest.mark.large
            def test_large():
                assert True

            @pytest.mark.xlarge
            def test_xlarge():
                assert True
            """,
            test_unsized="""
            def test_unsized_one():
                assert True

            def test_unsized_two():
                assert True
            """,
        )

        # When we run pytest with the --test-size-report flag
        result = pytester.runpytest('--test-size-report')

        # Then the output should include a summary of test sizes
        result.stdout.fnmatch_lines(
            [
                '*Test Size Report Summary*',
                '*Test Size Distribution:*',
                '*Small*1*test*(16.67%)*',
                '*Medium*1*test*(16.67%)*',
                '*Large*1*test*(16.67%)*',
                '*Xlarge*1*test*(16.67%)*',
                '*Unsized*2*tests*(33.33%)*',
                '*Total*6*tests*',
            ]
        )

    def it_generates_detailed_console_report(self, pytester: pytest.Pytester) -> None:
        """Verify detailed report generation with the --test-size-report=detailed flag."""
        # Given test files with various sized and unsized tests
        pytester.makepyfile(
            test_sized="""
            import pytest
            import time

            @pytest.mark.small
            def test_small():
                time.sleep(0.1)
                assert True

            @pytest.mark.medium
            def test_medium():
                time.sleep(0.2)
                assert True

            @pytest.mark.large
            def test_large():
                time.sleep(0.3)
                assert True

            @pytest.mark.xlarge
            def test_xlarge():
                time.sleep(0.4)
                assert True
            """,
            test_unsized="""
            import time

            def test_unsized_one():
                time.sleep(0.1)
                assert True

            def test_unsized_two():
                time.sleep(0.2)
                assert True
            """,
        )

        # When we run pytest with the --test-size-report=detailed flag
        result = pytester.runpytest('--test-size-report=detailed')

        # Then the output should include detailed test information
        # Check that the detailed report section exists
        assert 'Detailed Test Size Report' in result.stdout.str()

        # Check that all tests are present
        assert 'test_sized.py::test_small' in result.stdout.str()
        assert 'test_sized.py::test_medium' in result.stdout.str()
        assert 'test_sized.py::test_large' in result.stdout.str()
        assert 'test_sized.py::test_xlarge' in result.stdout.str()
        assert 'test_unsized.py::test_unsized_one' in result.stdout.str()
        assert 'test_unsized.py::test_unsized_two' in result.stdout.str()

        # Check that all tests show as Pass
        assert 'Pass' in result.stdout.str()

    def it_filters_report_to_specific_paths(self, pytester: pytest.Pytester) -> None:
        """Verify report generation can be filtered to specific test paths."""
        # Given tests in multiple directories
        dir1 = pytester.mkpydir('dir1')
        dir2 = pytester.mkpydir('dir2')

        # Tests in dir1
        dir1_file = dir1 / 'test_dir1.py'
        dir1_file.write_text("""import pytest

@pytest.mark.small
def test_small_dir1():
    assert True

@pytest.mark.medium
def test_medium_dir1():
    assert True
""")

        # Tests in dir2
        dir2_file = dir2 / 'test_dir2.py'
        dir2_file.write_text("""import pytest

@pytest.mark.large
def test_large_dir2():
    assert True

@pytest.mark.xlarge
def test_xlarge_dir2():
    assert True

def test_unsized_dir2():
    assert True
""")

        # When we run pytest with --test-size-report=basic on dir1 only
        # This makes it clear that 'basic' is the option value and dir1 is a path
        result = pytester.runpytest('--test-size-report=basic', str(dir1))

        # Then it should run successfully and only collect tests from dir1
        # Exit code 0 = success, 2 = interrupted (due to collection error), 5 = no tests collected
        assert result.ret in [0, 2, 5]

        # Check that the report shows only 2 tests (from dir1) and not 5 tests (from both dirs)
        assert 'Total: 2 tests' in result.stdout.str()
        assert 'Small: 1 test (50.00%)' in result.stdout.str()
        assert 'Medium: 1 test (50.00%)' in result.stdout.str()
        assert 'Large: 0 tests (0.00%)' in result.stdout.str()
        assert 'Xlarge: 0 tests (0.00%)' in result.stdout.str()

    def it_highlights_tests_exceeding_time_limits(self, pytester: pytest.Pytester) -> None:
        """Verify detailed report highlights tests that exceed their size time limit."""
        # Given test files with tests that exceed time limits
        pytester.makepyfile(
            test_slow="""
            import pytest
            import time

            @pytest.mark.small  # Small tests should be < 1s
            def test_small_slow():
                time.sleep(1.1)  # This exceeds the limit
                assert True

            @pytest.mark.small
            def test_small_fast():
                time.sleep(0.1)  # This is within the limit
                assert True
            """
        )

        # When we run pytest with the --test-size-report=detailed flag
        result = pytester.runpytest('--test-size-report=detailed')

        # Then the slow test should be highlighted in the report
        # Check that the detailed report section exists
        assert 'Detailed Test Size Report' in result.stdout.str()

        # Check that both tests are present with correct status
        assert 'test_slow.py::test_small_slow' in result.stdout.str()
        assert 'test_slow.py::test_small_fast' in result.stdout.str()
        assert 'SLOW' in result.stdout.str()
        assert 'Pass' in result.stdout.str()

    def it_includes_failed_tests_in_report(self, pytester: pytest.Pytester) -> None:
        """Verify that failed tests are properly included in the report."""
        # Given test files with failing tests
        pytester.makepyfile(
            test_failing="""
            import pytest

            @pytest.mark.small
            def test_small_pass():
                assert True

            @pytest.mark.medium
            def test_medium_fail():
                assert False
            """
        )

        # When we run pytest with the --test-size-report=detailed flag
        result = pytester.runpytest('--test-size-report=detailed')

        # Then the report should include the failed test
        # Check that the detailed report section exists
        assert 'Detailed Test Size Report' in result.stdout.str()

        # Check that both tests are present
        assert 'test_failing.py::test_small_pass' in result.stdout.str()
        assert 'test_failing.py::test_medium_fail' in result.stdout.str()

        # Check that we have both Pass and FAIL status
        assert 'Pass' in result.stdout.str()
        assert 'FAIL' in result.stdout.str()

    def it_handles_edge_case_with_no_tests(self, pytester: pytest.Pytester) -> None:
        """Verify report generation handles the case with no tests."""
        # Given no test files
        # Just create an empty directory
        empty_dir = pytester.mkpydir('empty')

        # When we run pytest with the --test-size-report=basic flag on the empty directory
        # This makes it clear that 'basic' is the option value and empty_dir is a path
        result = pytester.runpytest('--test-size-report=basic', str(empty_dir))

        # Then the report should handle the empty case gracefully
        # Check that it runs without error (exit code 5 means no tests collected, which is expected)
        assert result.ret in [0, 5]  # 0 = success, 5 = no tests collected

        # Check that we get a report with all zeroes
        assert 'Test Size Report Summary' in result.stdout.str()
        assert 'Small: 0 tests (0.00%)' in result.stdout.str()
        assert 'Medium: 0 tests (0.00%)' in result.stdout.str()
        assert 'Large: 0 tests (0.00%)' in result.stdout.str()
        assert 'Xlarge: 0 tests (0.00%)' in result.stdout.str()
        assert 'Unsized: 0 tests (0.00%)' in result.stdout.str()
        assert 'Total: 0 tests' in result.stdout.str()
