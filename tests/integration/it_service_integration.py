"""Integration tests for services with real adapters.

These tests verify that services work correctly when using production adapters
instead of test doubles. This validates the integration between the domain
logic (services) and infrastructure (adapters).

All tests use @pytest.mark.medium since they involve real infrastructure.
"""

from __future__ import annotations

import warnings
from typing import (
    TYPE_CHECKING,
    cast,
)

import pytest

from pytest_test_categories.adapters.pytest_adapter import (
    PytestItemAdapter,
    PytestWarningAdapter,
)
from pytest_test_categories.distribution.stats import DistributionStats
from pytest_test_categories.reporting import TestSizeReport
from pytest_test_categories.services import (
    DistributionValidationService,
    TestCountingService,
    TestDiscoveryService,
    TestReportingService,
    TimingValidationService,
)
from pytest_test_categories.timers import WallTimer
from pytest_test_categories.types import (
    TestSize,
    TestTimer,
    TimerState,
    TimingViolationError,
)

if TYPE_CHECKING:
    from collections.abc import (
        Iterable,
        MutableMapping,
    )

    from pytest_test_categories.services.test_counting import TestItemProtocol


@pytest.mark.medium
class DescribeTestDiscoveryServiceIntegration:
    """Integration tests for TestDiscoveryService with real adapters."""

    def it_finds_size_marker_on_real_test_item(self, pytester: pytest.Pytester) -> None:
        """Verify service finds size markers using real adapters."""
        source = """
import pytest

@pytest.mark.small
def test_small():
    assert True
"""
        items = pytester.getitems(source)
        adapter = PytestItemAdapter(items[0])
        warning_adapter = PytestWarningAdapter()

        service = TestDiscoveryService(warning_system=warning_adapter)
        size = service.find_test_size(adapter)

        assert size == TestSize.SMALL

    def it_finds_medium_marker_on_real_test_item(self, pytester: pytest.Pytester) -> None:
        """Verify service finds medium markers using real adapters."""
        source = """
import pytest

@pytest.mark.medium
def test_medium():
    assert True
"""
        items = pytester.getitems(source)
        adapter = PytestItemAdapter(items[0])
        warning_adapter = PytestWarningAdapter()

        service = TestDiscoveryService(warning_system=warning_adapter)
        size = service.find_test_size(adapter)

        assert size == TestSize.MEDIUM

    def it_finds_large_marker_on_real_test_item(self, pytester: pytest.Pytester) -> None:
        """Verify service finds large markers using real adapters."""
        source = """
import pytest

@pytest.mark.large
def test_large():
    assert True
"""
        items = pytester.getitems(source)
        adapter = PytestItemAdapter(items[0])
        warning_adapter = PytestWarningAdapter()

        service = TestDiscoveryService(warning_system=warning_adapter)
        size = service.find_test_size(adapter)

        assert size == TestSize.LARGE

    def it_finds_xlarge_marker_on_real_test_item(self, pytester: pytest.Pytester) -> None:
        """Verify service finds xlarge markers using real adapters."""
        source = """
import pytest

@pytest.mark.xlarge
def test_xlarge():
    assert True
"""
        items = pytester.getitems(source)
        adapter = PytestItemAdapter(items[0])
        warning_adapter = PytestWarningAdapter()

        service = TestDiscoveryService(warning_system=warning_adapter)
        size = service.find_test_size(adapter)

        assert size == TestSize.XLARGE

    def it_emits_warning_for_unmarked_test_with_real_adapter(self, pytester: pytest.Pytester) -> None:
        """Verify service emits real warnings for unmarked tests."""
        source = """
def test_unmarked():
    assert True
"""
        items = pytester.getitems(source)
        adapter = PytestItemAdapter(items[0])
        warning_adapter = PytestWarningAdapter()

        service = TestDiscoveryService(warning_system=warning_adapter)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            size = service.find_test_size(adapter)

        assert size is None
        assert len(caught) == 1
        assert 'Test has no size marker' in str(caught[0].message)

    def it_raises_error_for_multiple_markers_with_real_adapter(self, pytester: pytest.Pytester) -> None:
        """Verify service raises UsageError for multiple size markers."""
        source = """
import pytest

@pytest.mark.small
@pytest.mark.medium
def test_multi():
    assert True
"""
        items = pytester.getitems(source)
        adapter = PytestItemAdapter(items[0])
        warning_adapter = PytestWarningAdapter()

        service = TestDiscoveryService(warning_system=warning_adapter)

        with pytest.raises(pytest.UsageError, match='Test cannot have multiple size markers'):
            service.find_test_size(adapter)


@pytest.mark.medium
class DescribeTestCountingServiceIntegration:
    """Integration tests for TestCountingService with real adapters."""

    def it_counts_tests_by_size_with_real_items(self, pytester: pytest.Pytester) -> None:
        """Verify service counts tests correctly using real pytest items."""
        source = """
import pytest

@pytest.mark.small
def test_small_1():
    assert True

@pytest.mark.small
def test_small_2():
    assert True

@pytest.mark.medium
def test_medium():
    assert True

@pytest.mark.large
def test_large():
    assert True
"""
        items = pytester.getitems(source)
        warning_adapter = PytestWarningAdapter()

        service = TestCountingService()

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            # Cast items to satisfy type checker - pytest.Item satisfies TestItemProtocol
            stats = service.count_tests(cast('Iterable[TestItemProtocol]', items), warning_adapter)

        assert stats.counts.small == 2
        assert stats.counts.medium == 1
        assert stats.counts.large == 1
        assert stats.counts.xlarge == 0

    def it_handles_unmarked_tests_with_real_items(self, pytester: pytest.Pytester) -> None:
        """Verify service handles unmarked tests with real infrastructure."""
        source = """
import pytest

@pytest.mark.small
def test_marked():
    assert True

def test_unmarked():
    assert True
"""
        items = pytester.getitems(source)
        warning_adapter = PytestWarningAdapter()

        service = TestCountingService()

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            # Cast items to satisfy type checker - pytest.Item satisfies TestItemProtocol
            stats = service.count_tests(cast('Iterable[TestItemProtocol]', items), warning_adapter)

        # Only marked test is counted
        assert stats.counts.small == 1
        # Warning emitted for unmarked test
        warning_messages = [str(w.message) for w in caught]
        assert any('Test has no size marker' in msg for msg in warning_messages)


@pytest.mark.medium
class DescribeDistributionValidationServiceIntegration:
    """Integration tests for DistributionValidationService with real adapters."""

    def it_validates_good_distribution_without_warnings(self) -> None:
        """Verify service accepts good distribution without warnings."""
        # 80% small, 15% medium, 5% large - perfect distribution
        stats = DistributionStats.update_counts({TestSize.SMALL: 80, TestSize.MEDIUM: 15, TestSize.LARGE: 5})
        warning_adapter = PytestWarningAdapter()

        service = DistributionValidationService()

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            service.validate_distribution(stats, warning_adapter)

        # No warnings for good distribution
        assert len(caught) == 0

    def it_emits_warning_for_bad_distribution(self) -> None:
        """Verify service emits real warnings for bad distribution."""
        # 50% small, 50% large - bad distribution
        stats = DistributionStats.update_counts({TestSize.SMALL: 50, TestSize.LARGE: 50})
        warning_adapter = PytestWarningAdapter()

        service = DistributionValidationService()

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            service.validate_distribution(stats, warning_adapter)

        # Should emit warning
        assert len(caught) == 1
        assert 'Test distribution does not meet targets' in str(caught[0].message)


@pytest.mark.medium
class DescribeTimingValidationServiceIntegration:
    """Integration tests for TimingValidationService with real timers."""

    def it_validates_timing_within_limit(self) -> None:
        """Verify service accepts timing within limit."""
        service = TimingValidationService()

        # Small tests have 1 second limit - 0.5s is fine
        service.validate_timing(TestSize.SMALL, 0.5)  # Does not raise

    def it_raises_for_timing_exceeding_limit(self) -> None:
        """Verify service raises TimingViolationError for exceeded limit."""
        service = TimingValidationService()

        # Small tests have 1 second limit - 2s exceeds it
        with pytest.raises(TimingViolationError):
            service.validate_timing(TestSize.SMALL, 2.0)

    def it_extracts_duration_from_real_timer(self) -> None:
        """Verify service extracts duration from real WallTimer."""
        import time

        timer = WallTimer(state=TimerState.READY)
        timer.start()
        time.sleep(0.05)  # Short sleep
        timer.stop()

        service = TimingValidationService()
        duration = service.get_test_duration(timer, None)

        assert duration is not None
        assert duration >= 0.04  # At least 40ms (allowing for timing variance)
        assert duration < 0.5  # Well under 500ms

    def it_prefers_report_duration_over_timer(self) -> None:
        """Verify service prefers report duration over timer duration."""
        import time

        timer = WallTimer(state=TimerState.READY)
        timer.start()
        time.sleep(0.05)
        timer.stop()

        service = TimingValidationService()
        report_duration = 1.5

        duration = service.get_test_duration(timer, report_duration)

        # Uses report duration, not timer
        assert duration == report_duration

    def it_cleans_up_timers(self) -> None:
        """Verify service cleans up timer references."""
        timer = WallTimer(state=TimerState.READY)
        # Cast dict to MutableMapping[str, TestTimer] to satisfy type checker
        timers: MutableMapping[str, TestTimer] = cast(
            'MutableMapping[str, TestTimer]', {'test.py::test_example': timer}
        )

        service = TimingValidationService()
        service.cleanup_timer(timers, 'test.py::test_example')

        assert 'test.py::test_example' not in timers


@pytest.mark.medium
class DescribeTestReportingServiceIntegration:
    """Integration tests for TestReportingService with real reports."""

    def it_creates_report_when_option_is_set(self) -> None:
        """Verify service creates report when option value is set."""
        service = TestReportingService()

        report = service.create_report_if_requested('basic')

        assert report is not None
        assert isinstance(report, TestSizeReport)

    def it_returns_none_when_option_is_none(self) -> None:
        """Verify service returns None when option is None."""
        service = TestReportingService()

        report = service.create_report_if_requested(None)

        assert report is None

    def it_adds_tests_to_report(self) -> None:
        """Verify service adds tests to report correctly."""
        service = TestReportingService()
        report = TestSizeReport()

        service.add_test_to_report(report, 'test.py::test_small', TestSize.SMALL)
        service.add_test_to_report(report, 'test.py::test_medium', TestSize.MEDIUM)
        service.add_test_to_report(report, 'test.py::test_unsized', None)

        assert len(report.sized_tests[TestSize.SMALL]) == 1
        assert len(report.sized_tests[TestSize.MEDIUM]) == 1
        assert len(report.unsized_tests) == 1

    def it_updates_test_results(self) -> None:
        """Verify service updates test outcomes and durations."""
        service = TestReportingService()
        report = TestSizeReport()

        service.add_test_to_report(report, 'test.py::test_example', TestSize.SMALL)
        service.update_test_result(report, 'test.py::test_example', 'passed', 0.5)

        assert report.test_outcomes['test.py::test_example'] == 'passed'
        assert report.test_durations['test.py::test_example'] == 0.5


@pytest.mark.medium
class DescribeServiceOrchestration:
    """Integration tests for services working together."""

    def it_uses_discovery_and_counting_services_together(self, pytester: pytest.Pytester) -> None:
        """Verify discovery and counting services integrate correctly."""
        source = """
import pytest

@pytest.mark.small
def test_small_1():
    assert True

@pytest.mark.small
def test_small_2():
    assert True

@pytest.mark.medium
def test_medium():
    assert True
"""
        items = pytester.getitems(source)
        warning_adapter = PytestWarningAdapter()

        # Use counting service (which internally discovers sizes)
        counting_service = TestCountingService()

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            # Cast items to satisfy type checker - pytest.Item satisfies TestItemProtocol
            stats = counting_service.count_tests(cast('Iterable[TestItemProtocol]', items), warning_adapter)

        # Then use validation service
        validation_service = DistributionValidationService()

        with warnings.catch_warnings(record=True):
            warnings.simplefilter('always')
            validation_service.validate_distribution(stats, warning_adapter)

        # Verify the services work together
        assert stats.counts.small == 2
        assert stats.counts.medium == 1

    def it_uses_timing_and_reporting_services_together(self) -> None:
        """Verify timing and reporting services integrate correctly."""
        import time

        # Create real timer
        timer = WallTimer(state=TimerState.READY)
        timer.start()
        time.sleep(0.05)
        timer.stop()

        # Use timing service to get duration
        timing_service = TimingValidationService()
        duration = timing_service.get_test_duration(timer, None)

        # Use reporting service to record
        reporting_service = TestReportingService()
        report = TestSizeReport()

        reporting_service.add_test_to_report(report, 'test.py::test_example', TestSize.SMALL)
        reporting_service.update_test_result(report, 'test.py::test_example', 'passed', duration)

        assert report.test_durations['test.py::test_example'] == duration
        assert duration is not None
        assert duration > 0
