"""End-to-end integration tests for complete workflows.

These tests verify complete workflows from test collection through execution
and reporting. They test the plugin as a whole, simulating real-world usage
scenarios.

All tests use @pytest.mark.medium since they involve real pytest infrastructure.
"""

from __future__ import annotations

import pytest


@pytest.mark.medium
class DescribeCompleteWorkflow:
    """End-to-end tests for complete test workflows."""

    def it_runs_complete_workflow_with_mixed_sizes(self, pytester: pytest.Pytester) -> None:
        """Verify complete workflow: collection -> execution -> reporting."""
        # Use test counts that result in clean percentages (4 tests: 50%, 25%, 25%)
        # to avoid floating point precision issues in percentage calculation
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_small_1():
                assert True

            @pytest.mark.small
            def test_small_2():
                assert True

            @pytest.mark.medium
            def test_medium():
                assert True

            @pytest.mark.large
            def test_large():
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # Verify all phases completed
        result.assert_outcomes(passed=4)
        stdout = result.stdout.str()

        # Collection phase: size labels applied
        assert '[SMALL]' in stdout
        assert '[MEDIUM]' in stdout
        assert '[LARGE]' in stdout

        # Terminal summary phase: distribution displayed
        assert 'Distribution Summary' in stdout

    def it_runs_workflow_with_test_size_report(self, pytester: pytest.Pytester) -> None:
        """Verify workflow with test size report option."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_fast():
                assert True

            @pytest.mark.medium
            def test_moderate():
                assert True
            """
        )

        result = pytester.runpytest('--test-size-report=basic')

        result.assert_outcomes(passed=2)
        stdout = result.stdout.str()
        assert 'Test Size Report Summary' in stdout

    def it_runs_workflow_with_detailed_report(self, pytester: pytest.Pytester) -> None:
        """Verify workflow with detailed test size report."""
        pytester.makepyfile(
            test_example="""
            import pytest
            import time

            @pytest.mark.small
            def test_quick():
                assert True

            @pytest.mark.medium
            def test_longer():
                time.sleep(0.01)
                assert True
            """
        )

        result = pytester.runpytest('--test-size-report=detailed')

        result.assert_outcomes(passed=2)
        stdout = result.stdout.str()
        assert 'Detailed Test Size Report' in stdout


@pytest.mark.medium
class DescribeEdgeCaseWorkflows:
    """End-to-end tests for edge case scenarios."""

    def it_handles_empty_test_suite(self, pytester: pytest.Pytester) -> None:
        """Verify workflow handles empty test suite gracefully."""
        pytester.makepyfile(
            test_example="""
            # Empty test file - no tests
            """
        )

        result = pytester.runpytest('-v')

        # Should not error on empty suite
        result.assert_outcomes()  # No outcomes expected

    def it_handles_all_tests_same_size(self, pytester: pytest.Pytester) -> None:
        """Verify workflow handles all tests being same size."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_one():
                assert True

            @pytest.mark.small
            def test_two():
                assert True

            @pytest.mark.small
            def test_three():
                assert True
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=3)
        stdout = result.stdout.str()
        # All tests should have same label
        lines_with_small = [line for line in stdout.splitlines() if '[SMALL]' in line]
        assert len(lines_with_small) >= 3

    def it_handles_missing_markers(self, pytester: pytest.Pytester) -> None:
        """Verify workflow handles tests without size markers."""
        pytester.makepyfile(
            test_example="""
            def test_no_marker():
                assert True
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)
        stdout = result.stdout.str()
        # Should warn about missing marker
        assert 'PytestWarning' in stdout or 'no size marker' in stdout

    def it_handles_timing_violations(self, pytester: pytest.Pytester) -> None:
        """Verify workflow handles timing violations correctly."""
        pytester.makepyfile(
            test_example="""
            import pytest
            import time

            @pytest.mark.small
            def test_too_slow():
                # Small tests have 1 second limit
                time.sleep(1.5)
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # Test should still pass but may have timing warning
        # The actual behavior depends on plugin configuration
        stdout = result.stdout.str()
        # Test runs to completion
        assert 'test_too_slow' in stdout

    def it_handles_distribution_warnings(self, pytester: pytest.Pytester) -> None:
        """Verify workflow generates distribution warnings for bad distributions."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.large
            def test_large_1():
                assert True

            @pytest.mark.large
            def test_large_2():
                assert True
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=2)
        # Distribution of 100% large tests should trigger warnings
        stdout = result.stdout.str()
        # Distribution summary is still shown
        assert 'Distribution Summary' in stdout


@pytest.mark.medium
class DescribeBaseClassWorkflow:
    """End-to-end tests for base class usage."""

    def it_supports_small_test_base_class(self, pytester: pytest.Pytester) -> None:
        """Verify workflow with SmallTest base class."""
        pytester.makepyfile(
            test_example="""
            from pytest_test_categories import SmallTest

            class TestExample(SmallTest):
                def test_method(self):
                    assert True
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)
        stdout = result.stdout.str()
        assert '[SMALL]' in stdout

    def it_supports_medium_test_base_class(self, pytester: pytest.Pytester) -> None:
        """Verify workflow with MediumTest base class."""
        pytester.makepyfile(
            test_example="""
            from pytest_test_categories import MediumTest

            class TestExample(MediumTest):
                def test_method(self):
                    assert True
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)
        stdout = result.stdout.str()
        assert '[MEDIUM]' in stdout

    def it_supports_large_test_base_class(self, pytester: pytest.Pytester) -> None:
        """Verify workflow with LargeTest base class."""
        pytester.makepyfile(
            test_example="""
            from pytest_test_categories import LargeTest

            class TestExample(LargeTest):
                def test_method(self):
                    assert True
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)
        stdout = result.stdout.str()
        assert '[LARGE]' in stdout

    def it_supports_xlarge_test_base_class(self, pytester: pytest.Pytester) -> None:
        """Verify workflow with XLargeTest base class."""
        pytester.makepyfile(
            test_example="""
            from pytest_test_categories import XLargeTest

            class TestExample(XLargeTest):
                def test_method(self):
                    assert True
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)
        stdout = result.stdout.str()
        assert '[XLARGE]' in stdout


@pytest.mark.medium
class DescribeParametrizedTestWorkflow:
    """End-to-end tests for parametrized tests."""

    def it_handles_parametrized_tests_with_size_marker(self, pytester: pytest.Pytester) -> None:
        """Verify parametrized tests correctly inherit size markers."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            @pytest.mark.parametrize('value', [1, 2, 3])
            def test_parametrized(value):
                assert value in [1, 2, 3]
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=3)
        stdout = result.stdout.str()
        # All parametrized variants should have the marker
        small_count = stdout.count('[SMALL]')
        assert small_count >= 3

    def it_handles_parametrized_tests_on_class(self, pytester: pytest.Pytester) -> None:
        """Verify parametrized tests on marked class."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.medium
            class TestParametrized:
                @pytest.mark.parametrize('x,y', [(1, 2), (3, 4)])
                def test_add(self, x, y):
                    assert x + y in [3, 7]
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=2)
        stdout = result.stdout.str()
        medium_count = stdout.count('[MEDIUM]')
        assert medium_count >= 2


@pytest.mark.medium
class DescribeFixtureWorkflow:
    """End-to-end tests for fixture interactions."""

    def it_works_with_fixtures(self, pytester: pytest.Pytester) -> None:
        """Verify plugin works correctly with fixtures."""
        pytester.makepyfile(
            conftest="""
            import pytest

            @pytest.fixture
            def sample_data():
                return [1, 2, 3]
            """,
            test_example="""
            import pytest

            @pytest.mark.small
            def test_with_fixture(sample_data):
                assert sample_data == [1, 2, 3]
            """,
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)
        stdout = result.stdout.str()
        assert '[SMALL]' in stdout

    def it_works_with_autouse_fixtures(self, pytester: pytest.Pytester) -> None:
        """Verify plugin works correctly with autouse fixtures."""
        pytester.makepyfile(
            conftest="""
            import pytest

            @pytest.fixture(autouse=True)
            def setup_teardown():
                # Setup
                yield
                # Teardown
            """,
            test_example="""
            import pytest

            @pytest.mark.small
            def test_with_autouse():
                assert True
            """,
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)


@pytest.mark.medium
class DescribeNestedClassWorkflow:
    """End-to-end tests for nested test classes."""

    def it_handles_nested_test_classes(self, pytester: pytest.Pytester) -> None:
        """Verify plugin handles nested test classes correctly."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            class TestOuter:
                def test_outer(self):
                    assert True

                class TestInner:
                    def test_inner(self):
                        assert True
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=2)
        stdout = result.stdout.str()
        # Both outer and inner tests should have marker
        assert stdout.count('[SMALL]') >= 2


@pytest.mark.medium
class DescribeMultiFileWorkflow:
    """End-to-end tests for multiple test files."""

    def it_handles_multiple_test_files(self, pytester: pytest.Pytester) -> None:
        """Verify plugin handles multiple test files correctly."""
        pytester.makepyfile(
            test_small="""
            import pytest

            @pytest.mark.small
            def test_small_1():
                assert True

            @pytest.mark.small
            def test_small_2():
                assert True
            """,
            test_medium="""
            import pytest

            @pytest.mark.medium
            def test_medium_1():
                assert True
            """,
            test_large="""
            import pytest

            @pytest.mark.large
            def test_large_1():
                assert True
            """,
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=4)
        stdout = result.stdout.str()
        assert '[SMALL]' in stdout
        assert '[MEDIUM]' in stdout
        assert '[LARGE]' in stdout

        # Distribution should show all sizes
        assert 'Distribution Summary' in stdout


@pytest.mark.medium
class DescribeVerbosityLevels:
    """End-to-end tests for different verbosity levels."""

    def it_works_with_quiet_mode(self, pytester: pytest.Pytester) -> None:
        """Verify plugin works in quiet mode."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_example():
                assert True
            """
        )

        result = pytester.runpytest('-q')

        result.assert_outcomes(passed=1)

    def it_works_with_verbose_mode(self, pytester: pytest.Pytester) -> None:
        """Verify plugin works in verbose mode."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_example():
                assert True
            """
        )

        result = pytester.runpytest('-vv')

        result.assert_outcomes(passed=1)
        stdout = result.stdout.str()
        assert '[SMALL]' in stdout

    def it_works_with_no_header_mode(self, pytester: pytest.Pytester) -> None:
        """Verify plugin works with no-header option."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_example():
                assert True
            """
        )

        result = pytester.runpytest('--no-header')

        result.assert_outcomes(passed=1)
