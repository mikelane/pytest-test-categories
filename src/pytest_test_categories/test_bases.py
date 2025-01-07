"""Test base classes for size categorization, inspired by 'Software Engineering at Google'."""

from __future__ import annotations

import pytest


class SmallTest:
    """Tests individual behaviors in isolation (roughly 80% of tests).

    These tests should:
    - Be limited to a single thread (no file I/O, network, or external dependencies)
    - Test a single, specific behavior
    - Run quickly (<60s) and be deterministic
    - Be easy to code, maintain, and understand
    - Allow the use of test doubles (mocks, stubs, fakes)
    - Promote high coverage and serve as documentation
    - Prefer state testing over interaction testing

    Example:
        class MySmallTest(SmallTest):
            def test_example(self):
                # Test a single behavior
                assert 1 + 1 == 2

    """

    pytestmark = pytest.mark.small


class MediumTest:
    """Tests somewhat more complex behaviors (about 15% of tests).

    These tests should:
    - Test a single, specific behavior
    - Take a little longer than small tests (<300s)
    - Allow multiple threads and file I/O
    - Disallow network access
    - Optionally include a real database or a web UI

    Example:
        class MyMediumTest(MediumTest):
            def test_example(self):
                # Uses file I/O or multiple threads
                pass

    """

    pytestmark = pytest.mark.medium


class LargeTest:
    """Tests complex features (about 2.5-5% of tests).

    These tests should:
    - Allow access to multiple machines
    - Allow network access
    - Be reserved for system-level or end-to-end tests
    - Take longer to run (<900s)

    Example:
        class MyLargeTest(LargeTest):
            def test_example(self):
                # Possibly tests multiple machines or network dependencies
                pass

    """

    pytestmark = pytest.mark.large


class XLargeTest:
    """Tests truly enormous features (about 0-5% of tests).

    These tests should:
    - Allow access to multiple machines
    - Allow network access
    - Be reserved for system-level or end-to-end tests
    - Take longer to run (300s-1000s)

    Example:
        class MyXLargeTest(XLargeTest):
            def test_example(self):
                # Potentially massive integration or performance tests
                pass

    """

    pytestmark = pytest.mark.xlarge
