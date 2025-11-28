"""Integration tests for filesystem blocking pytest hooks.

These tests verify that filesystem blocking is properly integrated with pytest hooks:
- pytest_configure registers the allowed_paths ini option
- pytest_addoption adds CLI override for allowed paths
- pytest_runtest_call activates blocking for small tests
- tmp_path fixture is automatically allowed

All tests use @pytest.mark.medium since they involve real pytest infrastructure.
"""

from __future__ import annotations

import pytest


@pytest.mark.medium
class DescribeFilesystemBlockingConfiguration:
    """Integration tests for filesystem blocking configuration phase."""

    def it_provides_allowed_paths_cli_option(self, pytester: pytest.Pytester) -> None:
        """Verify plugin provides --test-categories-allowed-paths CLI option."""
        result = pytester.runpytest('--help')

        stdout = result.stdout.str()
        assert '--test-categories-allowed-paths' in stdout

    def it_registers_allowed_paths_ini_option(self, pytester: pytest.Pytester) -> None:
        """Verify plugin registers the test_categories_allowed_paths ini option."""
        pytester.makeini("""
            [pytest]
            test_categories_allowed_paths = /tmp/test
        """)
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_small():
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # Should not error on unknown ini option
        assert 'INTERNALERROR' not in result.stdout.str()
        assert 'unrecognized configuration option' not in result.stderr.str()


@pytest.mark.medium
class DescribeFilesystemBlockingForSmallTests:
    """Integration tests for filesystem blocking during small test execution."""

    def it_blocks_filesystem_for_small_tests_in_strict_mode(self, pytester: pytest.Pytester) -> None:
        """Verify filesystem is blocked for small tests when enforcement=strict."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_small_with_filesystem():
                with open('/etc/passwd', 'r') as f:
                    f.read()
            """
        )

        result = pytester.runpytest('-v')

        # Test should fail with FilesystemAccessViolationError
        stdout = result.stdout.str()
        assert 'FilesystemAccessViolationError' in stdout or 'HermeticityViolationError' in stdout
        result.assert_outcomes(failed=1)

    def it_allows_tmp_path_for_small_tests(self, pytester: pytest.Pytester) -> None:
        """Verify small tests can use pytest's tmp_path fixture."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            from pathlib import Path

            @pytest.mark.small
            def test_small_with_tmp_path(tmp_path: Path):
                # tmp_path should be allowed
                test_file = tmp_path / 'test.txt'
                test_file.write_text('hello')
                assert test_file.read_text() == 'hello'
            """
        )

        result = pytester.runpytest('-v')

        # Test should pass - tmp_path is automatically allowed
        result.assert_outcomes(passed=1)

    def it_allows_configured_paths_from_ini(self, pytester: pytest.Pytester) -> None:
        """Verify small tests can access paths configured in ini file."""
        # Create a temp file to use as allowed path
        test_dir = pytester.mkdir('allowed_dir')
        test_file = test_dir / 'data.txt'
        test_file.write_text('test data')

        # Escape backslashes for Windows compatibility in string literals
        escaped_path = str(test_file).replace('\\', '\\\\')

        pytester.makeini(f"""
            [pytest]
            test_categories_enforcement = strict
            test_categories_allowed_paths = {test_dir}
        """)
        pytester.makepyfile(
            test_example=f"""
            import pytest

            @pytest.mark.small
            def test_small_with_allowed_path():
                with open('{escaped_path}', 'r') as f:
                    content = f.read()
                assert content == 'test data'
            """
        )

        result = pytester.runpytest('-v')

        # Test should pass - path is in allowed list
        result.assert_outcomes(passed=1)

    def it_allows_configured_paths_from_cli(self, pytester: pytest.Pytester) -> None:
        """Verify CLI allowed paths override/extend ini settings."""
        # Create a temp file to use as allowed path
        test_dir = pytester.mkdir('cli_allowed_dir')
        test_file = test_dir / 'cli_data.txt'
        test_file.write_text('cli test data')

        # Escape backslashes for Windows compatibility in string literals
        escaped_path = str(test_file).replace('\\', '\\\\')

        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example=f"""
            import pytest

            @pytest.mark.small
            def test_small_with_cli_allowed_path():
                with open('{escaped_path}', 'r') as f:
                    content = f.read()
                assert content == 'cli test data'
            """
        )

        result = pytester.runpytest('-v', f'--test-categories-allowed-paths={test_dir}')

        # Test should pass - path is allowed via CLI
        result.assert_outcomes(passed=1)

    def it_does_not_block_filesystem_when_enforcement_off(self, pytester: pytest.Pytester) -> None:
        """Verify filesystem is not blocked when enforcement=off."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = off
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import os

            @pytest.mark.small
            def test_small_without_blocking():
                # Should be able to check if file exists
                assert os.path.exists('/etc/passwd') or True  # Always pass
            """
        )

        result = pytester.runpytest('-v')

        # Test should pass - no blocking
        result.assert_outcomes(passed=1)

    def it_defaults_to_off_enforcement_for_filesystem(self, pytester: pytest.Pytester) -> None:
        """Verify enforcement defaults to 'off' (opt-in feature)."""
        # No ini setting, no CLI option
        pytester.makepyfile(
            test_example="""
            import pytest
            from pathlib import Path

            @pytest.mark.small
            def test_small_without_config():
                # Filesystem operations should work by default
                Path('/tmp').exists()
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # Test should pass - default is no blocking
        result.assert_outcomes(passed=1)


@pytest.mark.medium
class DescribeFilesystemBlockingForOtherSizes:
    """Integration tests for filesystem blocking with non-small tests."""

    def it_does_not_block_medium_tests(self, pytester: pytest.Pytester) -> None:
        """Verify medium tests are not blocked from filesystem access."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            from pathlib import Path

            @pytest.mark.medium
            def test_medium_with_filesystem():
                # Medium tests should not be blocked
                Path('/tmp').exists()
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # Test should pass - medium tests aren't blocked
        result.assert_outcomes(passed=1)

    def it_does_not_block_large_tests(self, pytester: pytest.Pytester) -> None:
        """Verify large tests are not blocked from filesystem access."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            from pathlib import Path

            @pytest.mark.large
            def test_large_with_filesystem():
                # Large tests should not be blocked
                Path('/tmp').exists()
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # Test should pass - large tests aren't blocked
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
            from pathlib import Path

            def test_unsized_with_filesystem():
                # Tests without size markers should not be blocked
                Path('/tmp').exists()
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # Test should pass - unsized tests aren't blocked
        result.assert_outcomes(passed=1)


@pytest.mark.medium
class DescribeCombinedResourceBlocking:
    """Integration tests for combined network and filesystem blocking."""

    def it_blocks_both_network_and_filesystem_for_small_tests(self, pytester: pytest.Pytester) -> None:
        """Verify both network AND filesystem are blocked for small tests."""
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
        )

        result = pytester.runpytest('-v')

        # Both tests should fail
        result.assert_outcomes(failed=2)


@pytest.mark.medium
class DescribeFilesystemBlockingCleanup:
    """Integration tests for filesystem blocking cleanup."""

    def it_restores_open_after_test_failure(self, pytester: pytest.Pytester) -> None:
        """Verify builtins.open is restored even when test fails."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            from pathlib import Path

            @pytest.mark.small
            def test_failing_small():
                assert False  # This test fails

            @pytest.mark.medium
            def test_medium_after_failure(tmp_path: Path):
                # Open should be restored for this test
                test_file = tmp_path / 'test.txt'
                test_file.write_text('hello')
                assert test_file.read_text() == 'hello'
            """
        )

        result = pytester.runpytest('-v')

        # First test fails, second test passes (open restored)
        result.assert_outcomes(passed=1, failed=1)

    def it_restores_open_after_violation_error(self, pytester: pytest.Pytester) -> None:
        """Verify builtins.open is restored after a filesystem violation."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            from pathlib import Path

            @pytest.mark.small
            def test_violating_small():
                # This should fail with FilesystemAccessViolationError
                with open('/etc/passwd', 'r') as f:
                    f.read()

            @pytest.mark.medium
            def test_medium_after_violation(tmp_path: Path):
                # Open should be restored for this test
                test_file = tmp_path / 'test.txt'
                test_file.write_text('world')
                assert test_file.read_text() == 'world'
            """
        )

        result = pytester.runpytest('-v')

        # First test fails with violation, second test passes (open restored)
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
            from pathlib import Path

            @pytest.mark.small
            def test_small_1(tmp_path: Path):
                (tmp_path / 'f1.txt').write_text('1')
                assert True

            @pytest.mark.small
            def test_small_2(tmp_path: Path):
                (tmp_path / 'f2.txt').write_text('2')
                assert True

            @pytest.mark.small
            def test_small_3(tmp_path: Path):
                (tmp_path / 'f3.txt').write_text('3')
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # All tests should pass
        result.assert_outcomes(passed=3)
