"""A pytest plugin to enforce test timing constraints and size distributions.

The test limits are taken from the book Software Engineering at Google.
"""

from __future__ import annotations

from .distribution.stats import (
    DistributionStats,
    TestPercentages,
)
from .plugin import (
    pytest_addoption,
    pytest_collection_finish,
    pytest_collection_modifyitems,
    pytest_configure,
    pytest_runtest_makereport,
    pytest_runtest_protocol,
    pytest_terminal_summary,
)
from .reporting import TestSizeReport
from .test_bases import (
    LargeTest,
    MediumTest,
    SmallTest,
    XLargeTest,
)
from .timers import (
    FakeTimer,
    WallTimer,
)
from .types import (
    PluginState,
    TestSize,
    TestTimer,
    TimerState,
    TimingViolationError,
)

__version__ = '0.3.0'

__all__ = [
    'DistributionStats',
    'FakeTimer',
    'LargeTest',
    'MediumTest',
    'PluginState',
    'SmallTest',
    'TestPercentages',
    'TestSize',
    'TestSizeReport',
    'TestTimer',
    'TimerState',
    'TimingViolationError',
    'WallTimer',
    'XLargeTest',
    'pytest_addoption',
    'pytest_collection_finish',
    'pytest_collection_modifyitems',
    'pytest_configure',
    'pytest_runtest_makereport',
    'pytest_runtest_protocol',
    'pytest_terminal_summary',
]
