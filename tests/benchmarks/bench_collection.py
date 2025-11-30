"""Benchmarks for test collection overhead.

These benchmarks measure the overhead of:
- Marker detection during collection
- Test ID modification (appending size labels)
- Distribution statistics counting

Target: Collection overhead < 1% additional time
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from pytest_test_categories.services.test_discovery import TestDiscoveryService
from pytest_test_categories.types import TestSize
from tests._fixtures.test_item import FakeTestItem
from tests._fixtures.warning_system import FakeWarningSystem
from tests.benchmarks.conftest import FakeMarker

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_benchmark.fixture import BenchmarkFixture


class DescribeBenchCollectionOverhead:
    """Benchmarks for collection phase overhead."""

    @pytest.mark.medium
    def it_benchmarks_marker_detection_for_100_tests(self, benchmark: BenchmarkFixture) -> None:
        """Benchmark marker detection for 100 test items."""
        warning_system = FakeWarningSystem()
        service = TestDiscoveryService(warning_system=warning_system)

        items = [
            FakeTestItem(
                nodeid=f'test_module.py::test_func_{i}',
                markers={'small': FakeMarker('small')},
            )
            for i in range(100)
        ]

        def detect_markers() -> list[TestSize | None]:
            return [service.find_test_size(item) for item in items]

        result = benchmark(detect_markers)
        assert len(result) == 100
        assert all(size == TestSize.SMALL for size in result)

    @pytest.mark.medium
    def it_benchmarks_marker_detection_for_1000_tests(self, benchmark: BenchmarkFixture) -> None:
        """Benchmark marker detection for 1000 test items."""
        warning_system = FakeWarningSystem()
        service = TestDiscoveryService(warning_system=warning_system)

        items = [
            FakeTestItem(
                nodeid=f'test_module.py::test_func_{i}',
                markers={'small': FakeMarker('small')} if i % 2 == 0 else {'medium': FakeMarker('medium')},
            )
            for i in range(1000)
        ]

        def detect_markers() -> list[TestSize | None]:
            return [service.find_test_size(item) for item in items]

        result = benchmark(detect_markers)
        assert len(result) == 1000

    @pytest.mark.medium
    def it_benchmarks_marker_detection_for_10000_tests(self, benchmark: BenchmarkFixture) -> None:
        """Benchmark marker detection for 10000 test items (target: < 100ms)."""
        warning_system = FakeWarningSystem()
        service = TestDiscoveryService(warning_system=warning_system)

        sizes = [TestSize.SMALL, TestSize.MEDIUM, TestSize.LARGE, TestSize.XLARGE]
        items = [
            FakeTestItem(
                nodeid=f'test_module.py::test_func_{i}',
                markers={sizes[i % 4].marker_name: FakeMarker(sizes[i % 4].marker_name)},
            )
            for i in range(10000)
        ]

        def detect_markers() -> list[TestSize | None]:
            return [service.find_test_size(item) for item in items]

        result = benchmark(detect_markers)
        assert len(result) == 10000

    @pytest.mark.medium
    def it_benchmarks_nodeid_modification_for_1000_tests(self, benchmark: BenchmarkFixture) -> None:
        """Benchmark test node ID modification for 1000 test items."""
        items = [FakeTestItem(nodeid=f'test_module.py::test_func_{i}') for i in range(1000)]

        def modify_nodeids() -> None:
            for item in items:
                item.set_nodeid(f'{item.nodeid} [SMALL]')

        benchmark(modify_nodeids)

        for item in items:
            assert '[SMALL]' in item.nodeid

    @pytest.mark.medium
    def it_benchmarks_mixed_size_collection(
        self,
        benchmark: BenchmarkFixture,
        fake_test_items_factory: Callable[[int, TestSize | None], list[FakeTestItem]],
    ) -> None:
        """Benchmark collection with realistic distribution (80/15/5)."""
        warning_system = FakeWarningSystem()
        service = TestDiscoveryService(warning_system=warning_system)

        small_items = fake_test_items_factory(800, TestSize.SMALL)
        medium_items = fake_test_items_factory(150, TestSize.MEDIUM)
        large_items = fake_test_items_factory(40, TestSize.LARGE)
        xlarge_items = fake_test_items_factory(10, TestSize.XLARGE)

        all_items = small_items + medium_items + large_items + xlarge_items

        def process_collection() -> dict[TestSize, int]:
            counts: dict[TestSize, int] = {}
            for item in all_items:
                size = service.find_test_size(item)
                if size:
                    counts[size] = counts.get(size, 0) + 1
            return counts

        result = benchmark(process_collection)
        assert result[TestSize.SMALL] == 800
        assert result[TestSize.MEDIUM] == 150
        assert result[TestSize.LARGE] == 40
        assert result[TestSize.XLARGE] == 10
