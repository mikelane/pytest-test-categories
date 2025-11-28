"""Feature tests for network restriction enforcement.

This module tests end-to-end network restriction behavior through pytest's
plugin system. It verifies that:
- Small tests have ALL network access blocked
- Medium tests can access localhost but are blocked from external hosts
- Large/XLarge tests have full network access

Uses pytester fixture for full pytest integration testing.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.medium


@pytest.fixture(autouse=True)
def conftest_file(pytester: pytest.Pytester) -> None:
    """Create a conftest file with the test categories plugin registered."""
    pytester.makeconftest("""
        import pytest
        from pytest_test_categories.distribution.stats import DistributionStats

        @pytest.fixture
        def distribution_stats(request):
            return request.config.distribution_stats
    """)


class DescribeMediumTestNetworkRestriction:
    """Tests for medium test network restriction (localhost only)."""

    def it_allows_medium_tests_to_access_localhost(self, pytester: pytest.Pytester) -> None:
        """Medium tests can access localhost services."""
        pytester.makepyfile(
            test_medium_localhost="""
            import pytest
            import socket

            @pytest.mark.medium
            def test_medium_can_bind_localhost():
                '''Medium tests can create localhost socket.'''
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    # Binding to localhost is allowed for medium tests
                    sock.bind(('127.0.0.1', 0))
                    assert True
                finally:
                    sock.close()
            """
        )

        result = pytester.runpytest(
            '-v',
            '--test-categories-enforcement=strict',
        )

        result.assert_outcomes(passed=1)

    def it_blocks_medium_tests_from_external_hosts(self, pytester: pytest.Pytester) -> None:
        """Medium tests are blocked from accessing external hosts."""
        pytester.makepyfile(
            test_medium_external="""
            import pytest
            import socket

            from pytest_test_categories.exceptions import NetworkAccessViolationError

            @pytest.mark.medium
            def test_medium_blocked_from_external():
                '''Medium tests cannot access external hosts.'''
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    # Attempting to connect to external host should raise
                    with pytest.raises(NetworkAccessViolationError):
                        sock.connect(('example.com', 80))
                finally:
                    sock.close()
            """
        )

        result = pytester.runpytest(
            '-v',
            '--test-categories-enforcement=strict',
        )

        result.assert_outcomes(passed=1)


class DescribeSmallTestNetworkRestriction:
    """Tests for small test network restriction (all blocked)."""

    def it_blocks_small_tests_from_localhost(self, pytester: pytest.Pytester) -> None:
        """Small tests cannot access even localhost."""
        pytester.makepyfile(
            test_small_localhost="""
            import pytest
            import socket

            from pytest_test_categories.exceptions import NetworkAccessViolationError

            @pytest.mark.small
            def test_small_blocked_from_localhost():
                '''Small tests cannot access localhost.'''
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    with pytest.raises(NetworkAccessViolationError):
                        sock.connect(('127.0.0.1', 80))
                finally:
                    sock.close()
            """
        )

        result = pytester.runpytest(
            '-v',
            '--test-categories-enforcement=strict',
        )

        result.assert_outcomes(passed=1)

    def it_blocks_small_tests_from_external_hosts(self, pytester: pytest.Pytester) -> None:
        """Small tests cannot access external hosts."""
        pytester.makepyfile(
            test_small_external="""
            import pytest
            import socket

            from pytest_test_categories.exceptions import NetworkAccessViolationError

            @pytest.mark.small
            def test_small_blocked_from_external():
                '''Small tests cannot access external hosts.'''
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    with pytest.raises(NetworkAccessViolationError):
                        sock.connect(('example.com', 443))
                finally:
                    sock.close()
            """
        )

        result = pytester.runpytest(
            '-v',
            '--test-categories-enforcement=strict',
        )

        result.assert_outcomes(passed=1)


class DescribeLargeTestNetworkRestriction:
    """Tests for large test network restriction (all allowed)."""

    def it_allows_large_tests_full_network_access(self, pytester: pytest.Pytester) -> None:
        """Large tests can access any network."""
        pytester.makepyfile(
            test_large_network="""
            import pytest
            import socket

            @pytest.mark.large
            def test_large_can_bind_any():
                '''Large tests can create sockets without restriction.'''
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    # Binding is allowed for large tests
                    sock.bind(('127.0.0.1', 0))
                    assert True
                finally:
                    sock.close()
            """
        )

        result = pytester.runpytest(
            '-v',
            '--test-categories-enforcement=strict',
        )

        result.assert_outcomes(passed=1)


class DescribeNetworkModeEnum:
    """Tests for NetworkMode enum in types.py."""

    def it_exposes_network_mode_enum(self, pytester: pytest.Pytester) -> None:
        """NetworkMode enum is accessible from types module."""
        pytester.makepyfile(
            test_network_mode="""
            import pytest
            from pytest_test_categories.types import NetworkMode

            @pytest.mark.small
            def test_network_mode_values():
                '''NetworkMode enum has expected values.'''
                assert NetworkMode.BLOCK_ALL.value == 'block_all'
                assert NetworkMode.LOCALHOST_ONLY.value == 'localhost'
                assert NetworkMode.ALLOW_ALL.value == 'allow_all'
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)

    def it_maps_test_size_to_network_mode(self, pytester: pytest.Pytester) -> None:
        """TestSize has network_mode property returning appropriate NetworkMode."""
        pytester.makepyfile(
            test_size_network_mode="""
            import pytest
            from pytest_test_categories.types import TestSize, NetworkMode

            @pytest.mark.small
            def test_small_maps_to_block_all():
                assert TestSize.SMALL.network_mode == NetworkMode.BLOCK_ALL

            @pytest.mark.small
            def test_medium_maps_to_localhost_only():
                assert TestSize.MEDIUM.network_mode == NetworkMode.LOCALHOST_ONLY

            @pytest.mark.small
            def test_large_maps_to_allow_all():
                assert TestSize.LARGE.network_mode == NetworkMode.ALLOW_ALL

            @pytest.mark.small
            def test_xlarge_maps_to_allow_all():
                assert TestSize.XLARGE.network_mode == NetworkMode.ALLOW_ALL
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=4)
