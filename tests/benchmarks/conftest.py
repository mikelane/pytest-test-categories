from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from pytest_test_categories.distribution.stats import DistributionStats, TestCounts
from pytest_test_categories.reporting import TestSizeReport
from pytest_test_categories.services.test_discovery import TestDiscoveryService
from pytest_test_categories.types import TestSize
from tests._fixtures.test_item import FakeTestItem
from tests._fixtures.warning_system import FakeWarningSystem

if TYPE_CHECKING:
    from collections.abc import Callable


class FakeMarker:
    """Fake marker implementation for benchmark tests."""

    def __init__(self, name: str) -> None:
        self.name = name


@pytest.fixture
def fake_warning_system() -> FakeWarningSystem:
    """Provide a fake warning system for benchmarks."""
    return FakeWarningSystem()


@pytest.fixture
def test_discovery_service(fake_warning_system: FakeWarningSystem) -> TestDiscoveryService:
    """Provide a test discovery service for benchmarks."""
    return TestDiscoveryService(warning_system=fake_warning_system)


@pytest.fixture
def fake_test_items_factory() -> Callable[[int, TestSize | None], list[FakeTestItem]]:
    """Factory fixture to create fake test items with specified sizes."""

    def _create_items(count: int, size: TestSize | None = None) -> list[FakeTestItem]:
        items = []
        for i in range(count):
            markers = {}
            if size is not None:
                markers[size.marker_name] = FakeMarker(size.marker_name)
            items.append(FakeTestItem(nodeid=f'test_module.py::test_func_{i}', markers=markers))
        return items

    return _create_items


@pytest.fixture
def distribution_with_ideal() -> DistributionStats:
    """Provide distribution stats matching the ideal 80/15/5 distribution."""
    return DistributionStats(
        counts=TestCounts(
            small=800,
            medium=150,
            large=40,
            xlarge=10,
        )
    )


@pytest.fixture
def distribution_with_10k_tests() -> DistributionStats:
    """Provide distribution stats for 10,000 tests."""
    return DistributionStats(
        counts=TestCounts(
            small=8000,
            medium=1500,
            large=400,
            xlarge=100,
        )
    )


@pytest.fixture
def test_size_report_factory() -> Callable[[int], TestSizeReport]:
    """Factory fixture to create TestSizeReport with specified number of tests."""

    def _create_report(test_count: int) -> TestSizeReport:
        report = TestSizeReport()
        small_count = int(test_count * 0.8)
        medium_count = int(test_count * 0.15)
        large_count = int(test_count * 0.04)
        xlarge_count = test_count - small_count - medium_count - large_count

        for i in range(small_count):
            report.add_test(f'test_small_{i}.py::test_func', TestSize.SMALL, duration=0.001, outcome='passed')

        for i in range(medium_count):
            report.add_test(f'test_medium_{i}.py::test_func', TestSize.MEDIUM, duration=1.5, outcome='passed')

        for i in range(large_count):
            report.add_test(f'test_large_{i}.py::test_func', TestSize.LARGE, duration=60.0, outcome='passed')

        for i in range(xlarge_count):
            report.add_test(f'test_xlarge_{i}.py::test_func', TestSize.XLARGE, duration=120.0, outcome='passed')

        return report

    return _create_report
