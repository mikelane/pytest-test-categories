"""pytest-xdist compatibility module.

This module provides utilities and hooks for pytest-xdist compatibility.
When tests are run in parallel with xdist, each worker process maintains
its own plugin state. This module handles aggregating results from workers
back to the controller for accurate reporting.

Key concepts:
- Controller: The main pytest process that coordinates workers
- Workers: Subprocesses (gw0, gw1, etc.) that execute tests
- workeroutput: Dict on worker config for passing data to controller

Hooks used:
- pytest_sessionfinish (worker): Send stats via workeroutput
- pytest_testnodedown (controller): Aggregate stats from workers
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from pytest_test_categories.types import TestSize

if TYPE_CHECKING:
    import pytest

    from pytest_test_categories.distribution.stats import TestCounts
    from pytest_test_categories.reporting import TestSizeReport

# Environment variable set by xdist on worker processes
XDIST_WORKER_ENV = 'PYTEST_XDIST_WORKER'

# Keys for worker output data
WORKEROUTPUT_DISTRIBUTION_KEY = 'test_categories_distribution'
WORKEROUTPUT_REPORT_KEY = 'test_categories_report'


def is_xdist_worker() -> bool:
    """Check if current process is an xdist worker.

    Returns:
        True if running as an xdist worker, False otherwise.

    """
    return XDIST_WORKER_ENV in os.environ


def is_xdist_controller(config: pytest.Config) -> bool:
    """Check if current process is the xdist controller.

    The controller is the main pytest process when xdist is active.
    It coordinates workers but does not execute tests itself.

    Args:
        config: The pytest configuration object.

    Returns:
        True if this is the xdist controller, False otherwise.

    """
    # Check if xdist plugin is active
    if not config.pluginmanager.hasplugin('xdist'):
        return False

    # If we're not a worker and xdist is active, we're the controller
    # But only if there are workers configured (-n > 0)
    try:
        numprocesses = config.getoption('numprocesses', default=0)
        # numprocesses can be 'auto' string or int
        if numprocesses == 'auto' or (isinstance(numprocesses, int) and numprocesses > 0):
            return not is_xdist_worker()
    except (ValueError, TypeError):
        pass

    return False


def serialize_distribution_counts(counts: TestCounts) -> dict[str, int]:
    """Serialize TestCounts to a dict for worker output.

    Args:
        counts: The test counts to serialize.

    Returns:
        A dict that can be safely passed through workeroutput.

    """
    return {
        'small': counts.small,
        'medium': counts.medium,
        'large': counts.large,
        'xlarge': counts.xlarge,
    }


def deserialize_distribution_counts(data: dict[str, int]) -> dict[str, int]:
    """Deserialize distribution counts from worker output.

    Args:
        data: The serialized counts dict.

    Returns:
        A dict suitable for creating TestCounts.

    """
    return {
        'small': data.get('small', 0),
        'medium': data.get('medium', 0),
        'large': data.get('large', 0),
        'xlarge': data.get('xlarge', 0),
    }


def serialize_report_data(report: TestSizeReport) -> dict[str, object]:
    """Serialize TestSizeReport data for worker output.

    Args:
        report: The test size report to serialize.

    Returns:
        A dict that can be safely passed through workeroutput.

    """
    # Convert defaultdict to regular dict with string keys
    sized_tests: dict[str, list[str]] = {}
    for size in TestSize:
        sized_tests[size.value] = list(report.sized_tests.get(size, []))

    return {
        'sized_tests': sized_tests,
        'unsized_tests': list(report.unsized_tests),
        'test_durations': dict(report.test_durations),
        'test_outcomes': dict(report.test_outcomes),
    }


def _merge_sized_tests(target: TestSizeReport, sized_tests: object) -> None:
    """Merge sized tests from worker data into target report."""
    if not isinstance(sized_tests, dict):
        return
    for size_str, tests in sized_tests.items():
        if not isinstance(tests, list):
            continue
        try:
            size = TestSize(size_str)
        except ValueError:
            continue
        for nodeid in tests:
            if nodeid not in target.sized_tests[size]:
                target.sized_tests[size].append(nodeid)


def _merge_unsized_tests(target: TestSizeReport, unsized_tests: object) -> None:
    """Merge unsized tests from worker data into target report."""
    if not isinstance(unsized_tests, list):
        return
    for nodeid in unsized_tests:
        if nodeid not in target.unsized_tests:
            target.unsized_tests.append(nodeid)


def _merge_durations(target: TestSizeReport, durations: object) -> None:
    """Merge test durations from worker data into target report."""
    if not isinstance(durations, dict):
        return
    for nodeid, duration in durations.items():
        if isinstance(duration, (int, float)):
            target.test_durations[nodeid] = duration


def _merge_outcomes(target: TestSizeReport, outcomes: object) -> None:
    """Merge test outcomes from worker data into target report."""
    if not isinstance(outcomes, dict):
        return
    for nodeid, outcome in outcomes.items():
        if isinstance(outcome, str):
            target.test_outcomes[nodeid] = outcome


def merge_report_data(
    target: TestSizeReport,
    worker_data: dict[str, object],
) -> None:
    """Merge worker report data into target report.

    This modifies the target report in place, adding all tests from the worker.

    Args:
        target: The target report to merge into.
        worker_data: Serialized report data from a worker.

    """
    _merge_sized_tests(target, worker_data.get('sized_tests', {}))
    _merge_unsized_tests(target, worker_data.get('unsized_tests', []))
    _merge_durations(target, worker_data.get('test_durations', {}))
    _merge_outcomes(target, worker_data.get('test_outcomes', {}))
