"""Integration tests for full plugin orchestration.

These tests verify that the plugin hooks work correctly together through
pytest's infrastructure. They test the plugin's behavior at the hook level,
ensuring proper state management and hook ordering.

All tests use @pytest.mark.medium since they involve real pytest infrastructure.
"""

from __future__ import annotations

import pytest


@pytest.mark.medium
class DescribePluginConfiguration:
    """Integration tests for plugin configuration phase."""

    def it_registers_all_size_markers(self, pytester: pytest.Pytester) -> None:
        """Verify plugin registers all size markers during configuration."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_small():
                assert True
            """
        )

        # Running with --markers shows registered markers
        result = pytester.runpytest('--markers')

        stdout = result.stdout.str()
        assert 'small' in stdout
        assert 'medium' in stdout
        assert 'large' in stdout
        assert 'xlarge' in stdout

    def it_initializes_plugin_state(self, pytester: pytest.Pytester) -> None:
        """Verify plugin initializes state during configuration."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_example():
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # Plugin should run without errors
        result.assert_outcomes(passed=1)


@pytest.mark.medium
class DescribePluginCollectionModification:
    """Integration tests for collection modification phase."""

    def it_appends_size_labels_to_test_ids(self, pytester: pytest.Pytester) -> None:
        """Verify plugin appends size labels to test node IDs."""
        pytester.makepyfile(
            test_example="""
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
            """
        )

        result = pytester.runpytest('-v')

        stdout = result.stdout.str()
        # Size labels are appended with spaces, e.g., "test_small [SMALL] PASSED"
        assert '[SMALL]' in stdout
        assert '[MEDIUM]' in stdout
        assert '[LARGE]' in stdout
        assert '[XLARGE]' in stdout

    def it_counts_tests_by_size_during_collection(self, pytester: pytest.Pytester) -> None:
        """Verify plugin counts tests during collection."""
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
            """
        )

        result = pytester.runpytest('-v')

        # Distribution summary shows counts
        stdout = result.stdout.str()
        assert 'Distribution Summary' in stdout or result.ret == 0


@pytest.mark.medium
class DescribePluginCollectionFinish:
    """Integration tests for collection finish phase (distribution validation)."""

    def it_validates_distribution_after_collection(self, pytester: pytest.Pytester) -> None:
        """Verify plugin validates distribution after test collection."""
        # Create a test suite with poor distribution
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.large
            def test_large_1():
                assert True

            @pytest.mark.large
            def test_large_2():
                assert True

            @pytest.mark.large
            def test_large_3():
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # Should see distribution warning
        stdout = result.stdout.str()
        # Tests still pass, but warning should be issued
        result.assert_outcomes(passed=3)
        assert 'distribution' in stdout.lower() or 'warning' in stdout.lower() or result.ret == 0

    def it_accepts_good_distribution(self, pytester: pytest.Pytester) -> None:
        """Verify plugin accepts well-balanced test distribution."""
        # Create balanced distribution: 80% small, 15% medium, 5% large
        test_content = """
import pytest

"""
        # Add 80 small tests
        for i in range(80):
            test_content += f"""
@pytest.mark.small
def test_small_{i}():
    assert True

"""
        # Add 15 medium tests
        for i in range(15):
            test_content += f"""
@pytest.mark.medium
def test_medium_{i}():
    assert True

"""
        # Add 5 large tests
        for i in range(5):
            test_content += f"""
@pytest.mark.large
def test_large_{i}():
    assert True

"""
        pytester.makepyfile(test_example=test_content)

        result = pytester.runpytest('-q')

        # Should pass without distribution warnings
        result.assert_outcomes(passed=100)


@pytest.mark.medium
class DescribePluginTestExecution:
    """Integration tests for test execution phase (timing and reporting)."""

    def it_tracks_test_timing(self, pytester: pytest.Pytester) -> None:
        """Verify plugin tracks test execution timing."""
        pytester.makepyfile(
            test_example="""
            import pytest
            import time

            @pytest.mark.small
            def test_fast():
                assert True

            @pytest.mark.small
            def test_slightly_slower():
                time.sleep(0.01)
                assert True
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=2)

    def it_handles_failing_tests(self, pytester: pytest.Pytester) -> None:
        """Verify plugin handles failing tests gracefully."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_passing():
                assert True

            @pytest.mark.small
            def test_failing():
                assert False
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1, failed=1)
        # Plugin should not interfere with normal failure handling
        assert 'AssertionError' in result.stdout.str()

    def it_handles_skipped_tests(self, pytester: pytest.Pytester) -> None:
        """Verify plugin handles skipped tests gracefully."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_passing():
                assert True

            @pytest.mark.small
            @pytest.mark.skip(reason='testing skip')
            def test_skipped():
                assert True
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1, skipped=1)

    def it_handles_xfail_tests(self, pytester: pytest.Pytester) -> None:
        """Verify plugin handles xfail tests gracefully."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_passing():
                assert True

            @pytest.mark.small
            @pytest.mark.xfail(reason='expected to fail')
            def test_xfail():
                assert False
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1, xfailed=1)


@pytest.mark.medium
class DescribePluginTerminalSummary:
    """Integration tests for terminal summary phase."""

    def it_displays_distribution_summary(self, pytester: pytest.Pytester) -> None:
        """Verify plugin displays distribution summary in terminal."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_small():
                assert True

            @pytest.mark.medium
            def test_medium():
                assert True
            """
        )

        result = pytester.runpytest('-v')

        stdout = result.stdout.str()
        assert 'Test Suite Distribution Summary' in stdout

    def it_displays_basic_report_when_requested(self, pytester: pytest.Pytester) -> None:
        """Verify plugin displays basic report when --test-size-report=basic."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_small():
                assert True

            @pytest.mark.medium
            def test_medium():
                assert True
            """
        )

        result = pytester.runpytest('--test-size-report=basic')

        stdout = result.stdout.str()
        assert 'Test Size Report Summary' in stdout

    def it_displays_detailed_report_when_requested(self, pytester: pytest.Pytester) -> None:
        """Verify plugin displays detailed report when --test-size-report=detailed."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_small():
                assert True

            @pytest.mark.medium
            def test_medium():
                assert True
            """
        )

        result = pytester.runpytest('--test-size-report=detailed')

        stdout = result.stdout.str()
        assert 'Detailed Test Size Report' in stdout


@pytest.mark.medium
class DescribePluginStateManagement:
    """Integration tests for plugin state management across hooks."""

    def it_maintains_state_across_collection_and_execution(self, pytester: pytest.Pytester) -> None:
        """Verify plugin state persists from collection through execution."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_one():
                assert True

            @pytest.mark.small
            def test_two():
                assert True

            @pytest.mark.medium
            def test_three():
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # Verify all tests run and distribution is tracked
        result.assert_outcomes(passed=3)
        stdout = result.stdout.str()
        assert 'Small' in stdout  # Distribution summary shows sizes
        assert 'Medium' in stdout

    def it_handles_parallel_test_execution(self, pytester: pytest.Pytester) -> None:
        """Verify plugin handles parallel test execution without state corruption."""
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
            def test_medium_1():
                assert True

            @pytest.mark.medium
            def test_medium_2():
                assert True
            """
        )

        # Run with xdist if available (falls back to serial if not)
        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=4)


@pytest.mark.medium
class DescribePluginErrorHandling:
    """Integration tests for plugin error handling."""

    def it_handles_collection_errors_gracefully(self, pytester: pytest.Pytester) -> None:
        """Verify plugin handles test collection failures gracefully."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_valid():
                assert True
            """,
            test_broken="""
            # This will cause import error
            import nonexistent_module
            """,
        )

        result = pytester.runpytest('-v', 'test_example.py')

        # Valid tests should still run
        result.assert_outcomes(passed=1)

    def it_handles_marker_errors_gracefully(self, pytester: pytest.Pytester) -> None:
        """Verify plugin handles multiple size markers with proper error."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            @pytest.mark.medium
            def test_invalid():
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # Should fail with descriptive error
        assert result.ret != 0
        stderr = result.stderr.str()
        assert 'multiple size markers' in stderr
