"""Feature tests for external systems detection in medium tests.

Per Google's test sizes table, "Use external systems" is **Discouraged** (not
prohibited) for medium tests. This feature implements a warning mechanism when
medium tests appear to use external containerized systems.

These tests verify the end-to-end behavior:
- Medium tests that import testcontainers/docker get a warning
- Medium tests with allow_external_systems=True get no warning
- Large tests get no warning (external systems are expected)
- Small tests are unaffected (they have other restrictions)

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


class DescribeMediumTestExternalSystemsWarning:
    """Tests for external systems warning in medium tests."""

    def it_warns_when_medium_test_imports_testcontainers_module(
        self,
        pytester: pytest.Pytester,
    ) -> None:
        """Medium tests that import testcontainers modules get a warning."""
        # Simulate importing testcontainers by adding to sys.modules
        # Note: We don't clean up - this simulates real import behavior
        pytester.makepyfile(
            test_medium_testcontainers="""
            import pytest
            import sys
            from types import ModuleType

            @pytest.mark.medium
            def test_uses_testcontainers():
                '''Simulate importing testcontainers by adding to sys.modules.'''
                # Simulate testcontainers import by adding fake module
                # Real imports stay in sys.modules - we don't clean up
                if 'testcontainers' not in sys.modules:
                    fake_tc = ModuleType('testcontainers')
                    sys.modules['testcontainers'] = fake_tc
                # Test passes but should get warning
                assert True
            """
        )

        result = pytester.runpytest(
            '-v',
            '--test-categories-enforcement=warn',
            '-W',
            'default',  # Show all warnings
        )

        result.assert_outcomes(passed=1, warnings=1)
        # Check for warning about testcontainers in output
        output = result.stdout.str()
        assert 'testcontainers' in output
        assert 'ExternalSystemsWarning' in output

    def it_warns_when_medium_test_imports_docker_module(
        self,
        pytester: pytest.Pytester,
    ) -> None:
        """Medium tests that import docker SDK get a warning."""
        pytester.makepyfile(
            test_medium_docker="""
            import pytest
            import sys
            from types import ModuleType

            @pytest.mark.medium
            def test_uses_docker():
                '''Simulate importing docker by adding to sys.modules.'''
                # Real imports stay in sys.modules
                if 'docker' not in sys.modules:
                    fake_docker = ModuleType('docker')
                    sys.modules['docker'] = fake_docker
                assert True
            """
        )

        result = pytester.runpytest(
            '-v',
            '--test-categories-enforcement=warn',
            '-W',
            'default',
        )

        result.assert_outcomes(passed=1, warnings=1)
        output = result.stdout.str()
        assert 'docker' in output
        assert 'ExternalSystemsWarning' in output

    def it_does_not_warn_when_allow_external_systems_is_true(
        self,
        pytester: pytest.Pytester,
    ) -> None:
        """Medium tests with allow_external_systems=True get no warning."""
        pytester.makepyfile(
            test_medium_allowed="""
            import pytest
            import sys
            from types import ModuleType

            @pytest.mark.medium(allow_external_systems=True)
            def test_external_systems_allowed():
                '''Uses testcontainers but warning is suppressed.'''
                # Real imports stay in sys.modules
                if 'testcontainers' not in sys.modules:
                    fake_tc = ModuleType('testcontainers')
                    sys.modules['testcontainers'] = fake_tc
                assert True
            """
        )

        result = pytester.runpytest(
            '-v',
            '--test-categories-enforcement=warn',
            '-W',
            'default',
        )

        result.assert_outcomes(passed=1)
        # Should NOT have ExternalSystemsWarning
        assert 'ExternalSystemsWarning' not in result.stdout.str()

    def it_does_not_warn_when_no_external_systems_imported(
        self,
        pytester: pytest.Pytester,
    ) -> None:
        """Medium tests without external system imports get no warning."""
        pytester.makepyfile(
            test_medium_normal="""
            import pytest
            import json  # Normal import, not external system

            @pytest.mark.medium
            def test_normal_medium():
                '''Regular medium test without external systems.'''
                data = json.loads('{"key": "value"}')
                assert data['key'] == 'value'
            """
        )

        result = pytester.runpytest(
            '-v',
            '--test-categories-enforcement=warn',
            '-W',
            'default',
        )

        result.assert_outcomes(passed=1)
        assert 'ExternalSystemsWarning' not in result.stdout.str()


class DescribeLargeTestExternalSystems:
    """Tests verifying large tests get no external systems warning."""

    def it_does_not_warn_for_large_tests(
        self,
        pytester: pytest.Pytester,
    ) -> None:
        """Large tests can use external systems without warning."""
        pytester.makepyfile(
            test_large_external="""
            import pytest
            import sys
            from types import ModuleType

            @pytest.mark.large
            def test_large_with_external_systems():
                '''Large tests expect external systems - no warning needed.'''
                # Real imports stay in sys.modules
                if 'testcontainers' not in sys.modules:
                    fake_tc = ModuleType('testcontainers')
                    sys.modules['testcontainers'] = fake_tc
                if 'docker' not in sys.modules:
                    fake_docker = ModuleType('docker')
                    sys.modules['docker'] = fake_docker
                assert True
            """
        )

        result = pytester.runpytest(
            '-v',
            '--test-categories-enforcement=warn',
            '-W',
            'default',
        )

        result.assert_outcomes(passed=1)
        # Large tests should NOT get ExternalSystemsWarning
        assert 'ExternalSystemsWarning' not in result.stdout.str()


class DescribeEnforcementModeInteraction:
    """Tests for enforcement mode interaction with external systems detection."""

    def it_does_not_warn_when_enforcement_is_off(
        self,
        pytester: pytest.Pytester,
    ) -> None:
        """No warning when enforcement mode is OFF."""
        pytester.makepyfile(
            test_enforcement_off="""
            import pytest
            import sys
            from types import ModuleType

            @pytest.mark.medium
            def test_external_with_enforcement_off():
                '''External systems import with enforcement OFF.'''
                # Real imports stay in sys.modules
                if 'testcontainers' not in sys.modules:
                    fake_tc = ModuleType('testcontainers')
                    sys.modules['testcontainers'] = fake_tc
                assert True
            """
        )

        result = pytester.runpytest(
            '-v',
            '--test-categories-enforcement=off',
            '-W',
            'default',
        )

        result.assert_outcomes(passed=1)
        # No warning when enforcement is off
        assert 'ExternalSystemsWarning' not in result.stdout.str()

    def it_warns_when_enforcement_is_strict(
        self,
        pytester: pytest.Pytester,
    ) -> None:
        """Warning is still issued when enforcement mode is STRICT."""
        pytester.makepyfile(
            test_enforcement_strict="""
            import pytest
            import sys
            from types import ModuleType

            @pytest.mark.medium
            def test_external_with_enforcement_strict():
                '''External systems import with enforcement STRICT.'''
                # Real imports stay in sys.modules
                if 'testcontainers' not in sys.modules:
                    fake_tc = ModuleType('testcontainers')
                    sys.modules['testcontainers'] = fake_tc
                assert True
            """
        )

        result = pytester.runpytest(
            '-v',
            '--test-categories-enforcement=strict',
            '-W',
            'default',
        )

        result.assert_outcomes(passed=1, warnings=1)
        # Warning should still be issued in strict mode (external systems is warn-only)
        output = result.stdout.str()
        assert 'testcontainers' in output
        assert 'ExternalSystemsWarning' in output


class DescribeWarningMessage:
    """Tests for the warning message content."""

    def it_includes_package_name_in_warning(
        self,
        pytester: pytest.Pytester,
    ) -> None:
        """Warning message includes the detected package name."""
        pytester.makepyfile(
            test_warning_content="""
            import pytest
            import sys
            from types import ModuleType

            @pytest.mark.medium
            def test_warning_message():
                # Real imports stay in sys.modules
                if 'testcontainers' not in sys.modules:
                    fake_tc = ModuleType('testcontainers')
                    sys.modules['testcontainers'] = fake_tc
                assert True
            """
        )

        result = pytester.runpytest(
            '-v',
            '--test-categories-enforcement=warn',
            '-W',
            'default',
        )

        result.assert_outcomes(passed=1, warnings=1)
        # Warning should mention testcontainers
        output = result.stdout.str()
        assert 'testcontainers' in output

    def it_includes_remediation_suggestions(
        self,
        pytester: pytest.Pytester,
    ) -> None:
        """Warning message includes remediation suggestions."""
        pytester.makepyfile(
            test_warning_remediation="""
            import pytest
            import sys
            from types import ModuleType

            @pytest.mark.medium
            def test_remediation_suggestions():
                # Real imports stay in sys.modules
                if 'testcontainers' not in sys.modules:
                    fake_tc = ModuleType('testcontainers')
                    sys.modules['testcontainers'] = fake_tc
                assert True
            """
        )

        result = pytester.runpytest(
            '-v',
            '--test-categories-enforcement=warn',
            '-W',
            'default',
        )

        result.assert_outcomes(passed=1, warnings=1)
        # Warning should mention the marker option for suppression
        output = result.stdout.str()
        assert 'allow_external_systems' in output
