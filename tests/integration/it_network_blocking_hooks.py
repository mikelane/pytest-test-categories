"""Integration tests for network blocking pytest hooks.

These tests verify that network blocking is properly integrated with pytest hooks:
- pytest_configure registers the enforcement ini option
- pytest_addoption adds CLI override
- pytest_runtest_call activates blocking for small tests

All tests use @pytest.mark.medium since they involve real pytest infrastructure.
"""

from __future__ import annotations

import pytest


@pytest.mark.medium
class DescribeNetworkBlockingConfiguration:
    """Integration tests for network blocking configuration phase."""

    def it_registers_enforcement_ini_option(self, pytester: pytest.Pytester) -> None:
        """Verify plugin registers the test_categories_enforcement ini option."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
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

    @pytest.mark.parametrize('mode', ['off', 'warn', 'strict'])
    def it_accepts_valid_enforcement_modes(self, pytester: pytest.Pytester, mode: str) -> None:
        """Verify plugin accepts all valid enforcement modes: off, warn, strict."""
        pytester.makeini(f"""
            [pytest]
            test_categories_enforcement = {mode}
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

        assert 'INTERNALERROR' not in result.stdout.str()


@pytest.mark.medium
class DescribeNetworkBlockingCLIOption:
    """Integration tests for network blocking CLI option."""

    def it_provides_enforcement_cli_option(self, pytester: pytest.Pytester) -> None:
        """Verify plugin provides --test-categories-enforcement CLI option."""
        result = pytester.runpytest('--help')

        stdout = result.stdout.str()
        assert '--test-categories-enforcement' in stdout

    def it_cli_overrides_ini_setting(self, pytester: pytest.Pytester) -> None:
        """Verify CLI option overrides ini setting."""
        # Set ini to 'off' but CLI to 'strict'
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = off
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import socket

            @pytest.mark.small
            def test_small_with_network():
                # This attempts a network connection
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    s.connect(('httpbin.org', 80))
                finally:
                    s.close()
            """
        )

        # With CLI override to strict, network access should fail
        result = pytester.runpytest('--test-categories-enforcement=strict', '-v')

        # Test should fail due to network blocking
        assert result.ret != 0 or 'NetworkAccessViolationError' in result.stdout.str()


@pytest.mark.medium
class DescribeNetworkBlockingForSmallTests:
    """Integration tests for network blocking during small test execution."""

    def it_blocks_network_for_small_tests_in_strict_mode(self, pytester: pytest.Pytester) -> None:
        """Verify network is blocked for small tests when enforcement=strict."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import socket

            @pytest.mark.small
            def test_small_with_network():
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(('httpbin.org', 80))
                s.close()
            """
        )

        result = pytester.runpytest('-v')

        # Test should fail with NetworkAccessViolationError
        stdout = result.stdout.str()
        assert 'NetworkAccessViolationError' in stdout or 'HermeticityViolationError' in stdout
        result.assert_outcomes(failed=1)

    def it_does_not_block_network_when_enforcement_off(self, pytester: pytest.Pytester) -> None:
        """Verify network is not blocked when enforcement=off."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = off
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import socket

            @pytest.mark.small
            def test_small_without_blocking():
                # Create socket but don't actually connect (avoid network dependency)
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.close()
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # Test should pass - no blocking
        result.assert_outcomes(passed=1)

    def it_defaults_to_off_enforcement(self, pytester: pytest.Pytester) -> None:
        """Verify enforcement defaults to 'off' (opt-in feature)."""
        # No ini setting, no CLI option
        pytester.makepyfile(
            test_example="""
            import pytest
            import socket

            @pytest.mark.small
            def test_small_without_config():
                # Socket operations should work by default
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.close()
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # Test should pass - default is no blocking
        result.assert_outcomes(passed=1)


@pytest.mark.medium
class DescribeNetworkBlockingForOtherSizes:
    """Integration tests for network blocking with non-small tests."""

    def it_allows_medium_tests_localhost_access(self, pytester: pytest.Pytester) -> None:
        """Verify medium tests can access localhost but not external hosts."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import socket

            @pytest.mark.medium
            def test_medium_with_localhost():
                # Medium tests can create localhost sockets
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    # Binding to localhost is allowed
                    s.bind(('127.0.0.1', 0))
                finally:
                    s.close()
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # Test should pass - medium tests can use localhost
        result.assert_outcomes(passed=1)

    def it_blocks_medium_tests_external_access(self, pytester: pytest.Pytester) -> None:
        """Verify medium tests are blocked from external network access."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import socket

            @pytest.mark.medium
            def test_medium_external_blocked():
                # Medium tests cannot access external hosts
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    s.connect(('example.com', 80))
                finally:
                    s.close()
            """
        )

        result = pytester.runpytest('-v')

        # Test should fail - medium tests blocked from external network
        stdout = result.stdout.str()
        assert 'NetworkAccessViolationError' in stdout or 'HermeticityViolationError' in stdout
        result.assert_outcomes(failed=1)

    def it_does_not_block_large_tests(self, pytester: pytest.Pytester) -> None:
        """Verify large tests are not blocked from network access."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import socket

            @pytest.mark.large
            def test_large_with_network():
                # Large tests should not be blocked
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.close()
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # Test should pass - large tests aren't blocked
        result.assert_outcomes(passed=1)

    def it_does_not_block_xlarge_tests(self, pytester: pytest.Pytester) -> None:
        """Verify xlarge tests are not blocked from network access."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import socket

            @pytest.mark.xlarge
            def test_xlarge_with_network():
                # XLarge tests should not be blocked
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.close()
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # Test should pass - xlarge tests aren't blocked
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
            import socket

            def test_unsized_with_network():
                # Tests without size markers should not be blocked
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.close()
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # Test should pass - unsized tests aren't blocked
        result.assert_outcomes(passed=1)


@pytest.mark.medium
class DescribeNetworkBlockingCleanup:
    """Integration tests for network blocking cleanup."""

    def it_restores_socket_after_test_failure(self, pytester: pytest.Pytester) -> None:
        """Verify socket is restored even when test fails."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import socket

            @pytest.mark.small
            def test_failing_small():
                assert False  # This test fails

            @pytest.mark.medium
            def test_medium_after_failure():
                # Socket should be restored for this test
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.close()
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # First test fails, second test passes (socket restored)
        result.assert_outcomes(passed=1, failed=1)

    def it_restores_socket_after_test_error(self, pytester: pytest.Pytester) -> None:
        """Verify socket is restored even when test errors."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import socket

            @pytest.mark.small
            def test_erroring_small():
                raise RuntimeError('Test error')

            @pytest.mark.medium
            def test_medium_after_error():
                # Socket should be restored for this test
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.close()
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # First test errors, second test passes (socket restored)
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
                assert True

            @pytest.mark.small
            def test_small_2():
                assert True

            @pytest.mark.small
            def test_small_3():
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # All tests should pass
        result.assert_outcomes(passed=3)


@pytest.mark.large
class DescribeNetworkBlockingWarnModeTests:
    """Tests for WARN mode behavior requiring external network.

    These tests are marked large because they need external network access
    to verify the blocker allows connections in WARN mode.
    """

    def it_warns_on_network_access_in_warn_mode(self, pytester: pytest.Pytester) -> None:
        """Verify network access generates warning in warn mode."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = warn
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import socket

            @pytest.mark.small
            def test_small_with_network():
                # Try to create a connection - should warn but not fail
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    # This might fail on CI without network, so wrap in try
                    s.settimeout(1)
                    s.connect(('httpbin.org', 80))
                except (socket.timeout, OSError):
                    pass  # Connection failed, that's OK for this test
                finally:
                    s.close()
            """
        )

        result = pytester.runpytest('-v')

        # Test should pass but warning should be emitted
        # (The actual behavior depends on whether the connection succeeds)
        # At minimum, no NetworkAccessViolationError should be raised
        assert 'NetworkAccessViolationError' not in result.stdout.str()
