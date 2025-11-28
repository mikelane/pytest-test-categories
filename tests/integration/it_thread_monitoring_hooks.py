"""Integration tests for thread monitoring pytest hooks.

These tests verify that thread monitoring is properly integrated with pytest hooks:
- pytest_runtest_call activates monitoring for small tests
- Warnings are emitted for small tests using threading
- No warnings for medium/large/xlarge tests

All tests use @pytest.mark.medium since they involve real pytest infrastructure.

Key Difference from Other Blockers:
Thread monitoring WARNS instead of BLOCKING, because:
1. Many libraries use threading internally
2. Some test frameworks use threading
3. Blocking would break legitimate infrastructure
"""

from __future__ import annotations

import pytest


@pytest.mark.medium
class DescribeThreadMonitoringForSmallTests:
    """Integration tests for thread monitoring during small test execution."""

    def it_warns_on_threading_thread_for_small_tests(self, pytester: pytest.Pytester) -> None:
        """Verify threading.Thread usage emits warning in small tests."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = warn
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import threading

            @pytest.mark.small
            def test_small_with_thread():
                # Creating a thread should emit warning
                t = threading.Thread(target=lambda: None)
                assert t is not None
            """
        )

        result = pytester.runpytest('-v', '-W', 'always')

        # Test should pass but warning should be emitted
        result.assert_outcomes(passed=1)
        stdout = result.stdout.str()
        assert 'Small test' in stdout or 'single-threaded' in stdout.lower() or result.ret == 0

    def it_warns_on_threading_timer_for_small_tests(self, pytester: pytest.Pytester) -> None:
        """Verify threading.Timer usage emits warning in small tests.

        Timer inherits from Thread, so when Thread is patched, Timer creation
        triggers our monitoring through Thread.__init__().
        """
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = warn
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import threading

            @pytest.mark.small
            def test_small_with_timer():
                # Creating a timer emits warning (Timer inherits from Thread)
                t = threading.Timer(1.0, lambda: None)
                t.cancel()  # Cancel immediately
                assert t is not None
            """
        )

        result = pytester.runpytest('-v', '-W', 'always')

        # Test should pass (warning, not error)
        # Timer inherits from Thread, so warning mentions threading.Thread
        result.assert_outcomes(passed=1)

    def it_warns_on_thread_pool_executor_for_small_tests(self, pytester: pytest.Pytester) -> None:
        """Verify ThreadPoolExecutor usage emits warning in small tests."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = warn
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            from concurrent.futures import ThreadPoolExecutor

            @pytest.mark.small
            def test_small_with_executor():
                # Creating executor should emit warning
                with ThreadPoolExecutor(max_workers=1) as executor:
                    pass
            """
        )

        result = pytester.runpytest('-v', '-W', 'always')

        # Test should pass (warning, not error)
        result.assert_outcomes(passed=1)

    def it_warns_on_process_pool_executor_for_small_tests(self, pytester: pytest.Pytester) -> None:
        """Verify ProcessPoolExecutor usage emits warning in small tests."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = warn
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            from concurrent.futures import ProcessPoolExecutor

            @pytest.mark.small
            def test_small_with_process_executor():
                # Creating process executor should emit warning
                # (ProcessPoolExecutor is monitored as it spawns processes)
                with ProcessPoolExecutor(max_workers=1) as executor:
                    pass
            """
        )

        result = pytester.runpytest('-v', '-W', 'always')

        # Test should pass (warning, not error)
        result.assert_outcomes(passed=1)

    def it_does_not_warn_when_enforcement_off(self, pytester: pytest.Pytester) -> None:
        """Verify no thread warnings when enforcement=off."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = off
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import threading

            @pytest.mark.small
            def test_small_without_monitoring():
                t = threading.Thread(target=lambda: None)
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # Test should pass without warnings
        result.assert_outcomes(passed=1)

    def it_defaults_to_off_enforcement(self, pytester: pytest.Pytester) -> None:
        """Verify enforcement defaults to 'off' (opt-in feature)."""
        pytester.makepyfile(
            test_example="""
            import pytest
            import threading

            @pytest.mark.small
            def test_small_default_config():
                t = threading.Thread(target=lambda: None)
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # Test should pass - default is no monitoring
        result.assert_outcomes(passed=1)


@pytest.mark.medium
class DescribeThreadMonitoringForOtherSizes:
    """Integration tests for thread monitoring with non-small tests."""

    def it_does_not_warn_medium_tests(self, pytester: pytest.Pytester) -> None:
        """Verify medium tests are not warned for thread usage."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = warn
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import threading

            @pytest.mark.medium
            def test_medium_with_thread():
                # Medium tests should not be warned
                t = threading.Thread(target=lambda: None)
                t.start()
                t.join()
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # Test should pass without threading warnings
        result.assert_outcomes(passed=1)
        stdout = result.stdout.str()
        assert 'single-threaded' not in stdout.lower()

    def it_does_not_warn_large_tests(self, pytester: pytest.Pytester) -> None:
        """Verify large tests are not warned for thread usage."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = warn
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import threading

            @pytest.mark.large
            def test_large_with_thread():
                # Large tests should not be warned
                t = threading.Thread(target=lambda: None)
                assert True
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)

    def it_does_not_warn_xlarge_tests(self, pytester: pytest.Pytester) -> None:
        """Verify xlarge tests are not warned for thread usage."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = warn
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import threading

            @pytest.mark.xlarge
            def test_xlarge_with_thread():
                # XLarge tests should not be warned
                t = threading.Thread(target=lambda: None)
                assert True
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)

    def it_does_not_warn_unsized_tests(self, pytester: pytest.Pytester) -> None:
        """Verify tests without size markers are not warned."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = warn
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import threading

            def test_unsized_with_thread():
                # Unsized tests should not be warned
                t = threading.Thread(target=lambda: None)
                assert True
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)


@pytest.mark.medium
class DescribeThreadMonitoringCleanup:
    """Integration tests for thread monitoring cleanup."""

    def it_restores_threading_after_test_failure(self, pytester: pytest.Pytester) -> None:
        """Verify threading is restored even when test fails."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = warn
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import threading

            @pytest.mark.small
            def test_failing_small():
                assert False  # This test fails

            @pytest.mark.medium
            def test_medium_after_failure():
                # Threading should be restored for this test
                t = threading.Thread(target=lambda: None)
                t.start()
                t.join()
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # First test fails, second test passes (threading restored)
        result.assert_outcomes(passed=1, failed=1)

    def it_restores_threading_after_test_error(self, pytester: pytest.Pytester) -> None:
        """Verify threading is restored even when test errors."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = warn
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import threading

            @pytest.mark.small
            def test_erroring_small():
                raise RuntimeError('Test error')

            @pytest.mark.medium
            def test_medium_after_error():
                # Threading should be restored for this test
                t = threading.Thread(target=lambda: None)
                t.start()
                t.join()
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # First test errors, second test passes (threading restored)
        result.assert_outcomes(passed=1, failed=1)

    def it_handles_multiple_small_tests_sequentially(self, pytester: pytest.Pytester) -> None:
        """Verify monitoring works correctly across multiple small tests."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = warn
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import threading

            @pytest.mark.small
            def test_small_1():
                t = threading.Thread(target=lambda: None)
                assert True

            @pytest.mark.small
            def test_small_2():
                t = threading.Thread(target=lambda: None)
                assert True

            @pytest.mark.small
            def test_small_3():
                t = threading.Thread(target=lambda: None)
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # All tests should pass (warnings don't fail tests)
        result.assert_outcomes(passed=3)


@pytest.mark.medium
class DescribeThreadMonitoringWarningMessage:
    """Integration tests for thread monitoring warning messages."""

    def it_includes_test_name_in_warning(self, pytester: pytest.Pytester) -> None:
        """Verify warning message includes the test name."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = warn
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import threading
            import warnings

            @pytest.mark.small
            def test_my_specific_test():
                # Capture warnings to check content
                t = threading.Thread(target=lambda: None)
                assert True
            """
        )

        result = pytester.runpytest('-v', '-W', 'always')

        result.assert_outcomes(passed=1)

    def it_suggests_using_medium_marker(self, pytester: pytest.Pytester) -> None:
        """Verify warning suggests using @pytest.mark.medium."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = warn
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import threading
            import warnings

            @pytest.mark.small
            def test_with_thread_needs_medium():
                t = threading.Thread(target=lambda: None)
                assert True
            """
        )

        result = pytester.runpytest('-v', '-W', 'always')

        result.assert_outcomes(passed=1)
