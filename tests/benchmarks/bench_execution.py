"""Benchmarks for per-test execution overhead.

These benchmarks measure the overhead of:
- Timer start/stop operations
- Timing validation
- Duration extraction

Target: Per-test execution overhead < 1ms per test
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from pytest_test_categories.services.timing_validation import TimingValidationService
from pytest_test_categories.timers import FakeTimer, WallTimer
from pytest_test_categories.types import TestSize, TestTimer, TimerState

if TYPE_CHECKING:
    from pytest_benchmark.fixture import BenchmarkFixture


class DescribeBenchTimerOverhead:
    """Benchmarks for timer operations."""

    @pytest.mark.medium
    def it_benchmarks_wall_timer_start_stop_cycle(self, benchmark: BenchmarkFixture) -> None:
        """Benchmark WallTimer start/stop cycle (target: < 1ms)."""
        timer = WallTimer(state=TimerState.READY)

        def timer_cycle() -> float:
            timer.reset()
            timer.start()
            timer.stop()
            return timer.duration()

        result = benchmark(timer_cycle)
        assert result >= 0.0

    @pytest.mark.medium
    def it_benchmarks_fake_timer_start_stop_cycle(self, benchmark: BenchmarkFixture) -> None:
        """Benchmark FakeTimer start/stop cycle for comparison."""
        timer = FakeTimer(state=TimerState.READY)

        def timer_cycle() -> float:
            timer.reset()
            timer.start()
            timer.advance(0.001)
            timer.stop()
            return timer.duration()

        result = benchmark(timer_cycle)
        assert result == 0.001

    @pytest.mark.medium
    def it_benchmarks_1000_timer_cycles(self, benchmark: BenchmarkFixture) -> None:
        """Benchmark 1000 timer start/stop cycles (simulating 1000 tests)."""

        def run_1000_cycles() -> int:
            count = 0
            for _ in range(1000):
                timer = WallTimer(state=TimerState.READY)
                timer.start()
                timer.stop()
                timer.duration()
                count += 1
            return count

        result = benchmark(run_1000_cycles)
        assert result == 1000

    @pytest.mark.medium
    def it_benchmarks_timer_creation_overhead(self, benchmark: BenchmarkFixture) -> None:
        """Benchmark timer instance creation overhead."""

        def create_timer() -> WallTimer:
            return WallTimer(state=TimerState.READY)

        result = benchmark(create_timer)
        assert result.state == TimerState.READY


class DescribeBenchTimingValidation:
    """Benchmarks for timing validation operations."""

    @pytest.mark.medium
    def it_benchmarks_timing_validation_pass(self, benchmark: BenchmarkFixture) -> None:
        """Benchmark timing validation for passing test (within limit)."""
        service = TimingValidationService()

        def validate_timing() -> None:
            service.validate_timing(TestSize.SMALL, 0.5)

        benchmark(validate_timing)

    @pytest.mark.medium
    def it_benchmarks_timing_validation_1000_tests(self, benchmark: BenchmarkFixture) -> None:
        """Benchmark timing validation for 1000 tests."""
        service = TimingValidationService()

        test_data = [
            (TestSize.SMALL, 0.5),
            (TestSize.MEDIUM, 100.0),
            (TestSize.LARGE, 500.0),
            (TestSize.XLARGE, 600.0),
        ]

        def validate_1000_timings() -> int:
            count = 0
            for i in range(1000):
                size, duration = test_data[i % 4]
                service.validate_timing(size, duration)
                count += 1
            return count

        result = benchmark(validate_1000_timings)
        assert result == 1000

    @pytest.mark.medium
    def it_benchmarks_duration_extraction_from_timer(self, benchmark: BenchmarkFixture) -> None:
        """Benchmark duration extraction from timer."""
        service = TimingValidationService()
        timer = FakeTimer(state=TimerState.READY)
        timer.start()
        timer.advance(0.5)
        timer.stop()

        def extract_duration() -> float | None:
            return service.get_test_duration(timer, None)

        result = benchmark(extract_duration)
        assert result == 0.5


class DescribeBenchTimerCleanup:
    """Benchmarks for timer cleanup operations."""

    @pytest.mark.medium
    def it_benchmarks_timer_cleanup(self, benchmark: BenchmarkFixture) -> None:
        """Benchmark timer cleanup from timers dict."""
        service = TimingValidationService()

        timers: dict[str, TestTimer] = {}
        for i in range(100):
            timer = WallTimer(state=TimerState.READY)
            timer.start()
            timer.stop()
            timers[f'test_{i}'] = timer

        def cleanup_timer() -> None:
            timer = WallTimer(state=TimerState.READY)
            timer.start()
            timer.stop()
            timers['cleanup_test'] = timer
            service.cleanup_timer(timers, 'cleanup_test')

        benchmark(cleanup_timer)

    @pytest.mark.medium
    def it_benchmarks_full_test_timing_workflow(self, benchmark: BenchmarkFixture) -> None:
        """Benchmark complete timing workflow for a single test."""
        service = TimingValidationService()
        timers: dict[str, TestTimer] = {}

        def full_workflow() -> None:
            timer = WallTimer(state=TimerState.READY)
            timers['test_workflow'] = timer

            timer.start()
            timer.stop()

            duration = service.get_test_duration(timer, None)
            if duration is not None:
                service.validate_timing(TestSize.SMALL, duration)

            service.cleanup_timer(timers, 'test_workflow')

        benchmark(full_workflow)
