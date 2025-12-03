"""Centralized error registry for pytest-test-categories.

This module provides a centralized registry of error codes and message formatting
utilities for all violations and warnings in the plugin.

Each error code follows the format TC### where:
- TC = Test Categories prefix
- ### = Three-digit numeric identifier

Error Code Ranges:
- TC001-TC099: Resource isolation violations (network, filesystem, process, database, sleep)
- TC100-TC199: Timing violations
- TC200-TC299: Distribution warnings
- TC900-TC999: Internal errors

Example Usage:
    >>> from pytest_test_categories.errors import ERROR_CODES, format_error_message
    >>> error_code = ERROR_CODES['network_violation']
    >>> message = format_error_message(
    ...     error_code=error_code,
    ...     what_happened='Test attempted connection to api.example.com:443',
    ...     remediation=['Mock the network call', 'Use dependency injection']
    ... )
    >>> print(message)

See Also:
    - exceptions.py: Exception classes that use these error codes
    - timing.py: TimingViolationError that uses these error codes

"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    'ERROR_CODES',
    'ErrorCode',
    'format_error_message',
]

# Base URL for documentation
DOCS_BASE_URL = 'https://pytest-test-categories.readthedocs.io/en/latest'


@dataclass(frozen=True)
class ErrorCode:
    """A structured error code with associated metadata.

    Attributes:
        code: The error code (e.g., 'TC001').
        title: A short title describing the error.
        why_it_matters: Explanation of why this violation is important.
        doc_url: Full URL to the documentation for this error.

    Example:
        >>> error = ErrorCode(
        ...     code='TC001',
        ...     title='Network Access Violation',
        ...     why_it_matters='Small tests must be hermetic...',
        ...     doc_url='https://pytest-test-categories.readthedocs.io/...'
        ... )

    """

    code: str
    title: str
    why_it_matters: str
    doc_url: str


# =============================================================================
# Resource Isolation Violations (TC001-TC099)
# =============================================================================

NETWORK_VIOLATION = ErrorCode(
    code='TC001',
    title='Network Access Violation',
    why_it_matters=(
        'Small tests must be hermetic and cannot access the network. '
        'Network calls introduce non-determinism, external dependencies, '
        'and can cause flaky tests due to network latency or failures.'
    ),
    doc_url=f'{DOCS_BASE_URL}/errors/network-isolation.html',
)

FILESYSTEM_VIOLATION = ErrorCode(
    code='TC002',
    title='Filesystem Access Violation',
    why_it_matters=(
        'Small tests should not access the filesystem directly. '
        'Filesystem access introduces I/O overhead, potential race conditions, '
        'and dependencies on the test environment state.'
    ),
    doc_url=f'{DOCS_BASE_URL}/errors/filesystem-isolation.html',
)

SUBPROCESS_VIOLATION = ErrorCode(
    code='TC003',
    title='Subprocess Spawn Violation',
    why_it_matters=(
        'Small tests should run in a single process without spawning subprocesses. '
        'Subprocess spawning introduces non-determinism from external process behavior, '
        'I/O overhead from process creation, and timing variability that causes flaky tests.'
    ),
    doc_url=f'{DOCS_BASE_URL}/errors/process-isolation.html',
)

DATABASE_VIOLATION = ErrorCode(
    code='TC004',
    title='Database Access Violation',
    why_it_matters=(
        'Small tests should not connect to databases, even in-memory ones like sqlite3 :memory:. '
        'Database connections introduce I/O operations, external state dependencies, '
        'and additional complexity that can cause non-deterministic behavior.'
    ),
    doc_url=f'{DOCS_BASE_URL}/errors/database-isolation.html',
)

SLEEP_VIOLATION = ErrorCode(
    code='TC005',
    title='Sleep Call Violation',
    why_it_matters=(
        'Small tests should not call sleep functions. '
        'Using sleep in tests indicates waiting for async operations that should use proper '
        'synchronization, flaky timing assumptions, or polling patterns that should use '
        'condition-based waiting instead.'
    ),
    doc_url=f'{DOCS_BASE_URL}/errors/sleep-blocking.html',
)

# =============================================================================
# Timing Violations (TC100-TC199)
# =============================================================================

TIMING_VIOLATION = ErrorCode(
    code='TC006',
    title='Timing Violation',
    why_it_matters=(
        'Tests have time limits based on their size category. '
        'Exceeding the time limit indicates the test is doing too much work for its category, '
        'may have performance issues, or should be recategorized to a larger size.'
    ),
    doc_url=f'{DOCS_BASE_URL}/errors/timing-limits.html',
)

# =============================================================================
# Distribution Warnings (TC200-TC299)
# =============================================================================

DISTRIBUTION_WARNING = ErrorCode(
    code='TC007',
    title='Test Distribution Warning',
    why_it_matters=(
        "The test suite distribution does not match Google's recommended proportions. "
        'A healthy test suite should have ~80% small tests, ~15% medium tests, and ~5% large/xlarge tests. '
        'This distribution ensures fast feedback loops and efficient CI/CD pipelines.'
    ),
    doc_url=f'{DOCS_BASE_URL}/errors/distribution-targets.html',
)

# =============================================================================
# Error Code Registry
# =============================================================================

ERROR_CODES: dict[str, ErrorCode] = {
    'network_violation': NETWORK_VIOLATION,
    'filesystem_violation': FILESYSTEM_VIOLATION,
    'subprocess_violation': SUBPROCESS_VIOLATION,
    'database_violation': DATABASE_VIOLATION,
    'sleep_violation': SLEEP_VIOLATION,
    'timing_violation': TIMING_VIOLATION,
    'distribution_warning': DISTRIBUTION_WARNING,
}


def format_error_message(
    error_code: ErrorCode,
    what_happened: str,
    remediation: list[str],
    test_nodeid: str | None = None,
    test_size: str | None = None,
) -> str:
    """Format a standardized error message with remediation guidance.

    This function creates a consistently formatted error message that includes:
    1. Error code and title (for grep-friendly CI log parsing)
    2. Test context (nodeid, size) if provided
    3. What happened (specific violation details)
    4. Why it matters (explanation from error code)
    5. How to fix (bullet-point remediation options)
    6. Documentation link

    Args:
        error_code: The ErrorCode instance for this violation.
        what_happened: Description of what went wrong.
        remediation: List of remediation suggestions.
        test_nodeid: Optional pytest node ID of the failing test.
        test_size: Optional test size category name.

    Returns:
        A formatted multi-line error message string.

    Example:
        >>> error_code = ERROR_CODES['network_violation']
        >>> message = format_error_message(
        ...     error_code=error_code,
        ...     what_happened='Test attempted connection to api.example.com:443',
        ...     remediation=['Mock the network call', 'Use dependency injection'],
        ...     test_nodeid='tests/test_api.py::test_fetch',
        ...     test_size='SMALL',
        ... )

    """
    lines = [
        '',
        '=' * 70,
        f'[{error_code.code}] {error_code.title}',
        '=' * 70,
    ]

    # Add test context if available
    if test_nodeid:
        lines.append(f'Test: {test_nodeid}')
    if test_size:
        lines.append(f'Category: {test_size}')

    # What happened
    lines.extend(
        [
            '',
            'What happened:',
            f'  {what_happened}',
            '',
        ]
    )

    # Why it matters
    lines.extend(
        [
            'Why it matters:',
            f'  {error_code.why_it_matters}',
            '',
        ]
    )

    # How to fix
    lines.append('To fix this (choose one):')
    lines.extend(f'  \u2022 {step}' for step in remediation)
    lines.append('')

    # Documentation link
    lines.extend(
        [
            f'See: {error_code.doc_url}',
            '=' * 70,
        ]
    )

    return '\n'.join(lines)
