"""Integration tests for hermeticity violation summary in terminal output.

These tests verify that the hermeticity summary is displayed correctly
in the terminal output after test execution with violations.

All tests use @pytest.mark.large since they need to spawn subprocess tests
that have unrestricted network access to test the plugin's violation tracking.
"""

from __future__ import annotations

import pytest


@pytest.mark.large
class DescribeHermeticitySummaryOutput:
    """Integration tests for hermeticity summary display."""

    def it_shows_summary_when_network_violations_occur_in_warn_mode(self, pytester: pytest.Pytester) -> None:
        """Hermeticity summary is shown when network violations occur in WARN mode."""
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
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    # Attempt connection that triggers violation
                    s.settimeout(0.1)
                    try:
                        s.connect(('httpbin.org', 80))
                    except (socket.timeout, OSError):
                        pass  # Connection may fail, that's OK
                finally:
                    s.close()
            """
        )

        result = pytester.runpytest('-v')

        # Test passes in warn mode
        result.assert_outcomes(passed=1)
        stdout = result.stdout.str()

        # Should show hermeticity summary
        assert 'Hermeticity Violation Summary' in stdout
        assert 'enforcement: warn' in stdout
        assert 'Network:' in stdout

    def it_shows_summary_when_violations_occur_in_strict_mode(self, pytester: pytest.Pytester) -> None:
        """Hermeticity summary is shown when violations cause test failure in STRICT mode."""
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

        # Test fails in strict mode
        result.assert_outcomes(failed=1)
        stdout = result.stdout.str()

        # Should show hermeticity summary
        assert 'Hermeticity Violation Summary' in stdout
        assert 'enforcement: strict' in stdout
        assert 'Network:' in stdout
        # Should indicate test failed
        assert 'failed' in stdout.lower()

    def it_does_not_show_summary_when_no_violations(self, pytester: pytest.Pytester) -> None:
        """Hermeticity summary is not shown when no violations occur."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_small_clean():
                assert True
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)
        stdout = result.stdout.str()

        # Should NOT show hermeticity summary
        assert 'Hermeticity Violation Summary' not in stdout

    def it_shows_shorter_summary_in_quiet_mode(self, pytester: pytest.Pytester) -> None:
        """Hermeticity summary is condensed in quiet mode."""
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
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    s.settimeout(0.1)
                    try:
                        s.connect(('httpbin.org', 80))
                    except (socket.timeout, OSError):
                        pass
                finally:
                    s.close()
            """
        )

        result = pytester.runpytest('-q')

        # Test passes in warn mode
        result.assert_outcomes(passed=1)
        stdout = result.stdout.str()

        # Should show hermeticity summary even in quiet mode
        assert 'Hermeticity Violation Summary' in stdout

    def it_does_not_show_summary_when_enforcement_off(self, pytester: pytest.Pytester) -> None:
        """Hermeticity summary is not shown when enforcement is OFF."""
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
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.close()
                assert True
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)
        stdout = result.stdout.str()

        # Should NOT show hermeticity summary when enforcement is off
        assert 'Hermeticity Violation Summary' not in stdout


@pytest.mark.large
class DescribeHermeticitySummaryWithMultipleViolationTypes:
    """Integration tests for hermeticity summary with multiple violation types."""

    def it_shows_counts_by_violation_type(self, pytester: pytest.Pytester) -> None:
        """Hermeticity summary shows counts for each violation type."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = warn
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import socket
            import time

            @pytest.mark.small
            def test_network_violation():
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    s.settimeout(0.1)
                    try:
                        s.connect(('httpbin.org', 80))
                    except (socket.timeout, OSError):
                        pass
                finally:
                    s.close()

            @pytest.mark.small
            def test_sleep_violation():
                time.sleep(0.001)  # Any sleep is a violation for small tests
            """
        )

        result = pytester.runpytest('-v')

        # Both tests pass in warn mode
        result.assert_outcomes(passed=2)
        stdout = result.stdout.str()

        # Should show hermeticity summary with both violation types
        assert 'Hermeticity Violation Summary' in stdout
        # Should show counts for network and sleep
        assert 'Network:' in stdout
        assert 'Sleep:' in stdout

    def it_shows_remediation_guidance(self, pytester: pytest.Pytester) -> None:
        """Hermeticity summary includes remediation guidance."""
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
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    s.settimeout(0.1)
                    try:
                        s.connect(('httpbin.org', 80))
                    except (socket.timeout, OSError):
                        pass
                finally:
                    s.close()
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)
        stdout = result.stdout.str()

        # Should show remediation guidance
        assert 'To fix:' in stdout or 'Mock' in stdout
        # Should show documentation link
        assert 'Docs:' in stdout or 'readthedocs' in stdout
