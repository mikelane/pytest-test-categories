"""Test the categorization of tests by size."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(autouse=True)
def conftest_file(pytester: pytest.Pytester) -> Path:
    """Create a conftest file with the test categories plugin registered.

    This fixture is automatically used in all tests to ensure the plugin
    is properly registered with pytest.

    Args:
        pytester: The pytest fixture for testing pytest plugins.

    Returns:
        The path to the created conftest file.

    """
    return pytester.makeconftest("""
        from pytest_test_categories.plugin import TestCategories

        def pytest_configure(config):
            config.pluginmanager.register(TestCategories())
    """)


@pytest.fixture
def minimal_test_file(pytester: pytest.Pytester, request: pytest.FixtureRequest) -> Path:
    """Create a test file with a single test marked with the specified size."""
    test_size = request.param

    return pytester.makepyfile(
        test_file=f"""
        import pytest

        @pytest.mark.{test_size.lower()}
        def test_example():
            assert True
        """,
    )


class DescribeTestCategorization:
    @pytest.mark.parametrize(
        ('minimal_test_file', 'expected_label'),
        [
            pytest.param('small', '[SMALL]', id='small test'),
            pytest.param('medium', '[MEDIUM]', id='medium test'),
            pytest.param('large', '[LARGE]', id='large test'),
            pytest.param('xlarge', '[XLARGE]', id='xlarge test'),
        ],
        indirect=['minimal_test_file'],
    )
    def it_recognizes_test_size_when_marked_with_size_marker(
        self,
        pytester: pytest.Pytester,
        minimal_test_file: Path,
        expected_label: str,
    ) -> None:
        """Verify that tests are properly categorized in the output based on their size marker."""
        result: pytest.RunResult = pytester.runpytest('-vv', minimal_test_file)

        stdout = result.stdout.str()
        test_output_line = next(line for line in stdout.splitlines() if 'test_example' in line and 'PASSED' in line)
        assert (
            expected_label in test_output_line
        ), f'Test output should show size category {expected_label} next to test name'

    def it_raises_error_when_test_has_multiple_size_markers(self, pytester: pytest.Pytester) -> None:
        test_file = pytester.makepyfile(
            test_file="""
            import pytest

            @pytest.mark.small
            @pytest.mark.medium
            def test_example():
                assert True
            """,
        )

        result: pytest.RunResult = pytester.runpytest(test_file)

        assert result.ret != 0

        result.stderr.fnmatch_lines(['*Test cannot have multiple size markers: small, medium*'])

    def it_warns_when_test_has_no_size_marker(self, pytester: pytest.Pytester) -> None:
        """Verify that tests are properly categorized in the output based on their size marker."""
        test_file = pytester.makepyfile(
            test_file="""
            def test_example():
                assert True
            """,
        )

        result: pytest.RunResult = pytester.runpytest(test_file)

        assert result.ret == 0
        result.stdout.fnmatch_lines(['*PytestWarning: Test has no size marker: test_file.py::test_example'])

    def it_applies_class_level_marker_to_test_methods(self, pytester: pytest.Pytester) -> None:
        """Verify that a size marker on a test class applies to all test methods."""
        test_file = pytester.makepyfile(
            test_file="""
            import pytest

            @pytest.mark.small
            class TestExample:
                def test_method_one(self):
                    assert True

                def test_method_two(self):
                    assert True
            """,
        )

        result: pytest.RunResult = pytester.runpytest('-vv', test_file)

        stdout = result.stdout.str()
        test_lines = [line for line in stdout.splitlines() if 'test_method' in line and 'PASSED' in line]
        expected_number_of_test_lines = 2
        assert len(test_lines) == expected_number_of_test_lines
        assert all('[SMALL]' in line for line in test_lines)

    def it_raises_error_when_method_and_class_have_different_size_markers(self, pytester: pytest.Pytester) -> None:
        """Verify that having different size markers on class and method raises an error."""
        test_file = pytester.makepyfile(
            test_file="""
            import pytest

            @pytest.mark.small
            class TestExample:
                @pytest.mark.medium
                def test_method(self):
                    assert True
            """,
        )

        result: pytest.RunResult = pytester.runpytest(test_file)

        assert result.ret != 0
        result.stderr.fnmatch_lines(['*Test cannot have multiple size markers: small, medium*'])

    def it_handles_collection_errors_gracefully(self, pytester: pytest.Pytester) -> None:
        """Verify that the plugin handles test collection failures gracefully."""
        test_file = pytester.makepyfile(
            test_file="""
            import pytest

            # This will cause a collection error due to invalid syntax
            @pytest.mark.small
            def test_example()  # Missing colon and function body
            """,
        )

        result: pytest.RunResult = pytester.runpytest(test_file)

        # The test should fail due to syntax error
        assert result.ret != 0
        # But it shouldn't cause our plugin to raise additional errors
        assert 'Exception in pytest_runtest_makereport' not in result.stderr.str()

    def it_raises_error_when_test_inherits_multiple_size_markers(self, pytester: pytest.Pytester) -> None:
        """Verify that inheriting conflicting size markers from multiple parent classes raises an error."""
        test_file = pytester.makepyfile(
            test_file="""
            import pytest

            @pytest.mark.small
            class SmallTests:
                pass

            @pytest.mark.medium
            class MediumTests:
                pass

            class TestExample(SmallTests, MediumTests):
                def test_method(self):
                    assert True
            """,
        )

        result: pytest.RunResult = pytester.runpytest(test_file)

        assert result.ret != 0
        result.stderr.fnmatch_lines(['*Test cannot have multiple size markers: small, medium*'])

    def it_applies_size_marker_to_all_parametrized_variants(self, pytester: pytest.Pytester) -> None:
        """Verify that size markers are correctly applied to all parametrized test variants."""
        test_file = pytester.makepyfile(
            test_file="""
            import pytest

            @pytest.mark.small
            @pytest.mark.parametrize('value', [1, 2, 3])
            def test_example(value):
                assert value in [1, 2, 3]
            """,
        )

        result: pytest.RunResult = pytester.runpytest('-vv', test_file)

        stdout = result.stdout.str()
        test_lines = [line for line in stdout.splitlines() if 'test_example' in line and 'PASSED' in line]

        # Should have 3 test variants
        expected_number_of_test_lines = 3
        assert len(test_lines) == expected_number_of_test_lines
        # Each variant should have the size marker
        assert all('[SMALL]' in line for line in test_lines)

    def it_handles_nested_test_classes(self, pytester: pytest.Pytester) -> None:
        """Verify that size markers work correctly with nested test classes."""
        test_file = pytester.makepyfile(
            test_file="""
            import pytest

            @pytest.mark.small
            class TestOuter:
                def test_outer_method(self):
                    assert True

                class TestInner:
                    def test_inner_method(self):
                        assert True

                    class TestDeepNested:
                        def test_nested_method(self):
                            assert True
            """,
        )

        result: pytest.RunResult = pytester.runpytest('-vv', test_file)

        assert result.ret == 0
        stdout = result.stdout.str()
        test_lines = [line for line in stdout.splitlines() if 'test_' in line and 'PASSED' in line]

        expected_number_of_test_lines = 3
        assert len(test_lines) == expected_number_of_test_lines
        assert all('[SMALL]' in line for line in test_lines)
