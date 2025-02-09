"""Test suite for test type base classes."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytest_test_categories.types import TestSize


@pytest.fixture(autouse=True)
def test_file(pytester: pytest.Pytester, request: pytest.FixtureRequest) -> None:
    """Create a test file using the specified test base class."""
    test_size = request.param
    pytester.makepyfile(
        test_example=f"""
        from pytest_test_categories.test_bases import {test_size}Test

        class TestExample({test_size}Test):
            def test_one(self):
                assert True

            def test_two(self):
                assert True
        """
    )


class DescribeTestBaseClasses:
    @pytest.mark.parametrize(
        ('test_file', 'size'),
        [
            pytest.param('Small', 'SMALL', id='small test'),
            pytest.param('Medium', 'MEDIUM', id='medium test'),
            pytest.param('Large', 'LARGE', id='large test'),
            pytest.param('XLarge', 'XLARGE', id='extra large test'),
        ],
        indirect=['test_file'],
    )
    def it_applies_size_marker_through_canonical_base_class(
        self,
        pytester: pytest.Pytester,
        size: TestSize,
    ) -> None:
        """Verify that canonical size base classes apply appropriate markers."""
        result = pytester.runpytest('-vv')

        stdout = result.stdout.str()
        assert result.ret == 0
        for line in stdout.splitlines():
            if 'test_one' not in line and 'test_two' not in line:
                continue
            assert re.match(rf'test_example.py::TestExample::test_(one|two) \[{size}\]', line)
