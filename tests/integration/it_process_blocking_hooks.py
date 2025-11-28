"""Integration tests for process blocking pytest hooks.

These tests verify that process blocking is properly integrated with pytest hooks:
- pytest_runtest_call activates blocking for small tests
- subprocess.run, os.system, etc. are blocked for small tests
- Medium/large tests are not blocked

All tests use @pytest.mark.medium since they involve real pytest infrastructure
via pytester (which spawns subprocesses).
"""

from __future__ import annotations

import pytest


@pytest.mark.medium
class DescribeProcessBlockingForSmallTests:
    """Integration tests for process blocking during small test execution."""

    def it_blocks_subprocess_run_for_small_tests_in_strict_mode(self, pytester: pytest.Pytester) -> None:
        """Verify subprocess.run is blocked for small tests when enforcement=strict."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import subprocess

            @pytest.mark.small
            def test_small_with_subprocess():
                subprocess.run(['echo', 'hello'])
            """
        )

        result = pytester.runpytest('-v')

        stdout = result.stdout.str()
        assert 'SubprocessViolationError' in stdout or 'HermeticityViolationError' in stdout
        result.assert_outcomes(failed=1)

    def it_blocks_subprocess_popen_for_small_tests_in_strict_mode(self, pytester: pytest.Pytester) -> None:
        """Verify subprocess.Popen is blocked for small tests when enforcement=strict."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import subprocess

            @pytest.mark.small
            def test_small_with_popen():
                proc = subprocess.Popen(['echo', 'hello'])
                proc.wait()
            """
        )

        result = pytester.runpytest('-v')

        stdout = result.stdout.str()
        assert 'SubprocessViolationError' in stdout or 'HermeticityViolationError' in stdout
        result.assert_outcomes(failed=1)

    def it_blocks_subprocess_call_for_small_tests_in_strict_mode(self, pytester: pytest.Pytester) -> None:
        """Verify subprocess.call is blocked for small tests when enforcement=strict."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import subprocess

            @pytest.mark.small
            def test_small_with_call():
                subprocess.call(['echo', 'hello'])
            """
        )

        result = pytester.runpytest('-v')

        stdout = result.stdout.str()
        assert 'SubprocessViolationError' in stdout or 'HermeticityViolationError' in stdout
        result.assert_outcomes(failed=1)

    def it_blocks_subprocess_check_output_for_small_tests_in_strict_mode(self, pytester: pytest.Pytester) -> None:
        """Verify subprocess.check_output is blocked for small tests when enforcement=strict."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import subprocess

            @pytest.mark.small
            def test_small_with_check_output():
                subprocess.check_output(['echo', 'hello'])
            """
        )

        result = pytester.runpytest('-v')

        stdout = result.stdout.str()
        assert 'SubprocessViolationError' in stdout or 'HermeticityViolationError' in stdout
        result.assert_outcomes(failed=1)

    def it_blocks_os_system_for_small_tests_in_strict_mode(self, pytester: pytest.Pytester) -> None:
        """Verify os.system is blocked for small tests when enforcement=strict."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import os

            @pytest.mark.small
            def test_small_with_os_system():
                os.system('echo hello')
            """
        )

        result = pytester.runpytest('-v')

        stdout = result.stdout.str()
        assert 'SubprocessViolationError' in stdout or 'HermeticityViolationError' in stdout
        result.assert_outcomes(failed=1)

    def it_blocks_os_popen_for_small_tests_in_strict_mode(self, pytester: pytest.Pytester) -> None:
        """Verify os.popen is blocked for small tests when enforcement=strict."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import os

            @pytest.mark.small
            def test_small_with_os_popen():
                os.popen('echo hello').read()
            """
        )

        result = pytester.runpytest('-v')

        stdout = result.stdout.str()
        assert 'SubprocessViolationError' in stdout or 'HermeticityViolationError' in stdout
        result.assert_outcomes(failed=1)

    def it_does_not_block_subprocesses_when_enforcement_off(self, pytester: pytest.Pytester) -> None:
        """Verify subprocesses are not blocked when enforcement=off."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = off
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import subprocess

            @pytest.mark.small
            def test_small_without_blocking():
                result = subprocess.run(['echo', 'hello'], capture_output=True, text=True)
                assert 'hello' in result.stdout
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)

    def it_defaults_to_off_enforcement_for_process(self, pytester: pytest.Pytester) -> None:
        """Verify enforcement defaults to 'off' (opt-in feature)."""
        pytester.makepyfile(
            test_example="""
            import pytest
            import subprocess

            @pytest.mark.small
            def test_small_without_config():
                # Subprocess operations should work by default
                result = subprocess.run(['echo', 'hello'], capture_output=True, text=True)
                assert 'hello' in result.stdout
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)


@pytest.mark.medium
class DescribeProcessBlockingForOtherSizes:
    """Integration tests for process blocking with non-small tests."""

    def it_does_not_block_medium_tests(self, pytester: pytest.Pytester) -> None:
        """Verify medium tests are not blocked from subprocess access."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import subprocess

            @pytest.mark.medium
            def test_medium_with_subprocess():
                result = subprocess.run(['echo', 'hello'], capture_output=True, text=True)
                assert 'hello' in result.stdout
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)

    def it_does_not_block_large_tests(self, pytester: pytest.Pytester) -> None:
        """Verify large tests are not blocked from subprocess access."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import subprocess

            @pytest.mark.large
            def test_large_with_subprocess():
                result = subprocess.run(['echo', 'hello'], capture_output=True, text=True)
                assert 'hello' in result.stdout
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)

    def it_does_not_block_unsized_tests(self, pytester: pytest.Pytester) -> None:
        """Verify tests without size markers are not blocked."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import subprocess

            def test_unsized_with_subprocess():
                result = subprocess.run(['echo', 'hello'], capture_output=True, text=True)
                assert 'hello' in result.stdout
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)


@pytest.mark.medium
class DescribeProcessBlockingCleanup:
    """Integration tests for process blocking cleanup."""

    def it_restores_subprocess_after_test_failure(self, pytester: pytest.Pytester) -> None:
        """Verify subprocess functions are restored even when test fails."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import subprocess

            @pytest.mark.small
            def test_failing_small():
                assert False  # This test fails

            @pytest.mark.medium
            def test_medium_after_failure():
                # subprocess should be restored for this test
                result = subprocess.run(['echo', 'hello'], capture_output=True, text=True)
                assert 'hello' in result.stdout
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1, failed=1)

    def it_restores_subprocess_after_violation_error(self, pytester: pytest.Pytester) -> None:
        """Verify subprocess functions are restored after a violation."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import subprocess

            @pytest.mark.small
            def test_violating_small():
                subprocess.run(['echo', 'hello'])

            @pytest.mark.medium
            def test_medium_after_violation():
                result = subprocess.run(['echo', 'world'], capture_output=True, text=True)
                assert 'world' in result.stdout
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1, failed=1)

    def it_handles_multiple_small_tests_sequentially(self, pytester: pytest.Pytester) -> None:
        """Verify blocking works correctly across multiple small tests."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_small_1():
                # No subprocess, should pass
                assert 1 + 1 == 2

            @pytest.mark.small
            def test_small_2():
                # No subprocess, should pass
                assert 2 + 2 == 4

            @pytest.mark.small
            def test_small_3():
                # No subprocess, should pass
                assert 3 + 3 == 6
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=3)


@pytest.mark.medium
class DescribeCombinedResourceBlocking:
    """Integration tests for combined resource blocking (network + filesystem + process)."""

    def it_blocks_all_resources_for_small_tests(self, pytester: pytest.Pytester) -> None:
        """Verify network, filesystem, AND subprocess are blocked for small tests."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_network="""
            import pytest
            import socket

            @pytest.mark.small
            def test_small_with_network():
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(('httpbin.org', 80))
                s.close()
            """,
            test_filesystem="""
            import pytest

            @pytest.mark.small
            def test_small_with_filesystem():
                with open('/etc/passwd', 'r') as f:
                    f.read()
            """,
            test_subprocess="""
            import pytest
            import subprocess

            @pytest.mark.small
            def test_small_with_subprocess():
                subprocess.run(['echo', 'hello'])
            """,
        )

        result = pytester.runpytest('-v')

        # All three tests should fail due to resource violations
        result.assert_outcomes(failed=3)
