"""Test the database blocker adapters.

This module tests both the FakeDatabaseBlocker (test adapter) and
DatabasePatchingBlocker (production adapter) implementations.

The database blockers follow hexagonal architecture:
- DatabaseBlockerPort is the Port (interface)
- FakeDatabaseBlocker is a Test Adapter (test double)
- DatabasePatchingBlocker is a Production Adapter (real implementation)

This follows the same pattern as the network, filesystem, and process blocker modules.

Database isolation ensures small tests remain hermetic by blocking:
- sqlite3.connect (including :memory:)
- Optional: psycopg2, psycopg, pymysql, pymongo, redis, sqlalchemy

Note: S108 warnings about /tmp paths are suppressed because these are symbolic
test values for testing argument handling, not actual insecure temp file usage.
"""
# ruff: noqa: S108

from __future__ import annotations

import pytest
from icontract import ViolationError

from pytest_test_categories.adapters.database import DatabasePatchingBlocker
from pytest_test_categories.adapters.fake_database import FakeDatabaseBlocker
from pytest_test_categories.exceptions import DatabaseViolationError
from pytest_test_categories.ports.database import (
    DatabaseAccessAttempt,
    is_coverage_data_file,
)
from pytest_test_categories.ports.network import (
    BlockerState,
    EnforcementMode,
)
from pytest_test_categories.types import TestSize


@pytest.mark.small
class DescribeFakeDatabaseBlocker:
    """Tests for the FakeDatabaseBlocker test double."""

    def it_starts_in_inactive_state(self) -> None:
        """Verify the blocker initializes in INACTIVE state."""
        blocker = FakeDatabaseBlocker()

        assert blocker.state == BlockerState.INACTIVE

    def it_transitions_to_active_on_activate(self) -> None:
        """Verify activate() transitions from INACTIVE to ACTIVE."""
        blocker = FakeDatabaseBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        assert blocker.state == BlockerState.ACTIVE

    def it_transitions_to_inactive_on_deactivate(self) -> None:
        """Verify deactivate() transitions from ACTIVE to INACTIVE."""
        blocker = FakeDatabaseBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        blocker.deactivate()

        assert blocker.state == BlockerState.INACTIVE

    def it_fails_to_activate_when_already_active(self) -> None:
        """Verify activate() raises when already ACTIVE."""
        blocker = FakeDatabaseBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        with pytest.raises(ViolationError, match='INACTIVE'):
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

    def it_fails_to_deactivate_when_inactive(self) -> None:
        """Verify deactivate() raises when already INACTIVE."""
        blocker = FakeDatabaseBlocker()

        with pytest.raises(ViolationError, match='ACTIVE'):
            blocker.deactivate()

    def it_records_activation_parameters(self) -> None:
        """Verify the blocker records test size and enforcement mode."""
        blocker = FakeDatabaseBlocker()

        blocker.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        assert blocker.current_test_size == TestSize.MEDIUM
        assert blocker.current_enforcement_mode == EnforcementMode.WARN

    def it_blocks_all_database_access_for_small_tests(self) -> None:
        """Verify small tests cannot access any database."""
        blocker = FakeDatabaseBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        assert blocker.check_connection_allowed('sqlite3', ':memory:') is False
        assert blocker.check_connection_allowed('sqlite3', '/tmp/test.db') is False
        assert blocker.check_connection_allowed('psycopg2', 'postgresql://localhost/db') is False

    def it_allows_all_database_access_for_medium_tests(self) -> None:
        """Verify medium tests can access any database."""
        blocker = FakeDatabaseBlocker()
        blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)

        assert blocker.check_connection_allowed('sqlite3', ':memory:') is True
        assert blocker.check_connection_allowed('sqlite3', '/tmp/test.db') is True
        assert blocker.check_connection_allowed('psycopg2', 'postgresql://localhost/db') is True

    def it_allows_all_database_access_for_large_tests(self) -> None:
        """Verify large tests can access any database."""
        blocker = FakeDatabaseBlocker()
        blocker.activate(TestSize.LARGE, EnforcementMode.STRICT)

        assert blocker.check_connection_allowed('sqlite3', ':memory:') is True
        assert blocker.check_connection_allowed('psycopg2', 'postgresql://remote/db') is True

    def it_allows_all_database_access_for_xlarge_tests(self) -> None:
        """Verify xlarge tests can access any database."""
        blocker = FakeDatabaseBlocker()
        blocker.activate(TestSize.XLARGE, EnforcementMode.STRICT)

        assert blocker.check_connection_allowed('sqlite3', ':memory:') is True
        assert blocker.check_connection_allowed('pymongo', 'mongodb://cluster/db') is True

    def it_records_connection_attempts(self) -> None:
        """Verify the blocker tracks database connection attempts."""
        blocker = FakeDatabaseBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        blocker.check_connection_allowed('sqlite3', ':memory:')
        blocker.check_connection_allowed('psycopg2', 'postgresql://localhost/db')

        assert len(blocker.connection_attempts) == 2
        assert blocker.connection_attempts[0] == DatabaseAccessAttempt(
            library='sqlite3',
            connection_string=':memory:',
            test_nodeid='',
            allowed=False,
        )
        assert blocker.connection_attempts[1] == DatabaseAccessAttempt(
            library='psycopg2',
            connection_string='postgresql://localhost/db',
            test_nodeid='',
            allowed=False,
        )

    def it_raises_on_violation_in_strict_mode(self) -> None:
        """Verify on_violation raises DatabaseViolationError in STRICT mode."""
        blocker = FakeDatabaseBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        with pytest.raises(DatabaseViolationError) as exc_info:
            blocker.on_violation('sqlite3', ':memory:', 'test_module.py::test_fn')

        assert exc_info.value.library == 'sqlite3'
        assert exc_info.value.connection_string == ':memory:'
        assert exc_info.value.test_size == TestSize.SMALL

    def it_records_warning_in_warn_mode(self) -> None:
        """Verify on_violation records warning in WARN mode."""
        blocker = FakeDatabaseBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.WARN)

        blocker.on_violation('sqlite3', '/tmp/test.db', 'test_module.py::test_fn')

        assert len(blocker.warnings) == 1
        assert 'sqlite3' in blocker.warnings[0]
        assert 'test.db' in blocker.warnings[0]

    def it_does_nothing_in_off_mode(self) -> None:
        """Verify on_violation does nothing in OFF mode."""
        blocker = FakeDatabaseBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.OFF)

        blocker.on_violation('sqlite3', ':memory:', 'test_module.py::test_fn')

        assert len(blocker.warnings) == 0

    def it_fails_check_connection_when_inactive(self) -> None:
        """Verify check_connection_allowed raises when INACTIVE."""
        blocker = FakeDatabaseBlocker()

        with pytest.raises(ViolationError, match='ACTIVE'):
            blocker.check_connection_allowed('sqlite3', ':memory:')

    def it_fails_on_violation_when_inactive(self) -> None:
        """Verify on_violation raises when INACTIVE."""
        blocker = FakeDatabaseBlocker()

        with pytest.raises(ViolationError, match='ACTIVE'):
            blocker.on_violation('sqlite3', ':memory:', 'test::fn')

    def it_resets_to_initial_state(self) -> None:
        """Verify reset() returns blocker to initial state."""
        blocker = FakeDatabaseBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        blocker.check_connection_allowed('sqlite3', ':memory:')

        blocker.reset()

        assert blocker.state == BlockerState.INACTIVE
        assert blocker.current_test_size is None
        assert blocker.current_enforcement_mode is None
        assert len(blocker.connection_attempts) == 0
        assert len(blocker.warnings) == 0

    def it_resets_even_when_active(self) -> None:
        """Verify reset() works regardless of current state."""
        blocker = FakeDatabaseBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        blocker.reset()

        assert blocker.state == BlockerState.INACTIVE

    def it_tracks_call_counts(self) -> None:
        """Verify the blocker tracks method invocation counts."""
        blocker = FakeDatabaseBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        blocker.check_connection_allowed('sqlite3', ':memory:')
        blocker.check_connection_allowed('psycopg2', 'host=localhost')
        blocker.deactivate()

        assert blocker.activate_count == 1
        assert blocker.deactivate_count == 1
        assert blocker.check_count == 2


@pytest.mark.small
class DescribeDatabasePatchingBlocker:
    """Tests for the DatabasePatchingBlocker production adapter."""

    def it_starts_in_inactive_state(self) -> None:
        """Verify the blocker initializes in INACTIVE state."""
        blocker = DatabasePatchingBlocker()

        assert blocker.state == BlockerState.INACTIVE

    def it_transitions_to_active_on_activate(self) -> None:
        """Verify activate() transitions from INACTIVE to ACTIVE."""
        blocker = DatabasePatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        assert blocker.state == BlockerState.ACTIVE

        blocker.deactivate()

    def it_transitions_to_inactive_on_deactivate(self) -> None:
        """Verify deactivate() transitions from ACTIVE to INACTIVE."""
        blocker = DatabasePatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        blocker.deactivate()

        assert blocker.state == BlockerState.INACTIVE

    def it_fails_to_activate_when_already_active(self) -> None:
        """Verify activate() raises when already ACTIVE."""
        blocker = DatabasePatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        try:
            with pytest.raises(ViolationError, match='INACTIVE'):
                blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        finally:
            blocker.reset()

    def it_fails_to_deactivate_when_inactive(self) -> None:
        """Verify deactivate() raises when already INACTIVE."""
        blocker = DatabasePatchingBlocker()

        with pytest.raises(ViolationError, match='ACTIVE'):
            blocker.deactivate()

    def it_stores_activation_parameters(self) -> None:
        """Verify the blocker stores test size and enforcement mode."""
        blocker = DatabasePatchingBlocker()

        blocker.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        assert blocker.current_test_size == TestSize.MEDIUM
        assert blocker.current_enforcement_mode == EnforcementMode.WARN

        blocker.deactivate()

    def it_blocks_all_database_access_for_small_tests(self) -> None:
        """Verify small tests cannot access any database."""
        blocker = DatabasePatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        assert blocker.check_connection_allowed('sqlite3', ':memory:') is False
        assert blocker.check_connection_allowed('sqlite3', '/tmp/test.db') is False

        blocker.deactivate()

    def it_allows_all_database_access_for_medium_tests(self) -> None:
        """Verify medium tests can access any database."""
        blocker = DatabasePatchingBlocker()
        blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)

        assert blocker.check_connection_allowed('sqlite3', ':memory:') is True
        assert blocker.check_connection_allowed('psycopg2', 'postgresql://localhost/db') is True

        blocker.deactivate()

    def it_allows_all_database_access_for_large_tests(self) -> None:
        """Verify large tests can access any database."""
        blocker = DatabasePatchingBlocker()
        blocker.activate(TestSize.LARGE, EnforcementMode.STRICT)

        assert blocker.check_connection_allowed('sqlite3', ':memory:') is True

        blocker.deactivate()

    def it_raises_on_violation_in_strict_mode(self) -> None:
        """Verify on_violation raises DatabaseViolationError in STRICT mode."""
        blocker = DatabasePatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        with pytest.raises(DatabaseViolationError) as exc_info:
            blocker.on_violation('sqlite3', ':memory:', 'test_module.py::test_fn')

        assert exc_info.value.library == 'sqlite3'
        assert exc_info.value.connection_string == ':memory:'

        blocker.deactivate()

    def it_resets_to_initial_state(self) -> None:
        """Verify reset() returns blocker to initial state."""
        blocker = DatabasePatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        blocker.reset()

        assert blocker.state == BlockerState.INACTIVE
        assert blocker.current_test_size is None
        assert blocker.current_enforcement_mode is None

    def it_patches_sqlite3_connect_on_activate(self) -> None:
        """Verify sqlite3.connect is patched when activated."""
        import sqlite3

        original_connect = sqlite3.connect
        blocker = DatabasePatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        assert sqlite3.connect is not original_connect

        blocker.deactivate()

        assert sqlite3.connect is original_connect

    def it_restores_sqlite3_connect_on_deactivate(self) -> None:
        """Verify sqlite3.connect is restored when deactivated."""
        import sqlite3

        original_connect = sqlite3.connect
        blocker = DatabasePatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        blocker.deactivate()

        assert sqlite3.connect is original_connect

    def it_restores_sqlite3_connect_on_reset(self) -> None:
        """Verify sqlite3.connect is restored on reset."""
        import sqlite3

        original_connect = sqlite3.connect
        blocker = DatabasePatchingBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        blocker.reset()

        assert sqlite3.connect is original_connect


@pytest.mark.small
class DescribeDatabaseViolationError:
    """Tests for the DatabaseViolationError exception."""

    def it_stores_library_and_connection_string(self) -> None:
        """Verify the exception stores library and connection string."""
        error = DatabaseViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='test_module.py::test_fn',
            library='sqlite3',
            connection_string=':memory:',
        )

        assert error.library == 'sqlite3'
        assert error.connection_string == ':memory:'

    def it_stores_test_context(self) -> None:
        """Verify the exception stores test size and nodeid."""
        error = DatabaseViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_db.py::test_query',
            library='psycopg2',
            connection_string='postgresql://localhost/db',
        )

        assert error.test_size == TestSize.SMALL
        assert error.test_nodeid == 'tests/test_db.py::test_query'

    def it_includes_library_in_message(self) -> None:
        """Verify the error message includes the library."""
        error = DatabaseViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='test_module.py::test_fn',
            library='sqlite3',
            connection_string=':memory:',
        )

        assert 'sqlite3' in str(error)

    def it_includes_connection_string_in_message(self) -> None:
        """Verify the error message includes the connection string."""
        error = DatabaseViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='test_module.py::test_fn',
            library='psycopg2',
            connection_string='postgresql://localhost/db',
        )

        assert 'postgresql://localhost/db' in str(error)

    def it_includes_remediation_for_small_tests(self) -> None:
        """Verify remediation suggestions are included for small tests."""
        error = DatabaseViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='test_module.py::test_fn',
            library='sqlite3',
            connection_string=':memory:',
        )

        message = str(error)
        assert 'mock' in message.lower() or 'Mock' in message
        assert 'medium' in message.lower()

    def it_includes_sqlalchemy_specific_remediation(self) -> None:
        """Verify SQLAlchemy-specific remediation is included."""
        error = DatabaseViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='test_module.py::test_fn',
            library='sqlalchemy',
            connection_string='sqlite:///:memory:',
        )

        message = str(error)
        assert 'SQLAlchemy' in message

    def it_has_no_remediation_for_medium_tests(self) -> None:
        """Verify no remediation for medium tests since database is allowed."""
        error = DatabaseViolationError(
            test_size=TestSize.MEDIUM,
            test_nodeid='test_module.py::test_fn',
            library='sqlite3',
            connection_string=':memory:',
        )

        # Should not include remediation suggestions for medium tests
        assert error.remediation == []


@pytest.mark.small
class DescribeDatabaseAccessAttempt:
    """Tests for the DatabaseAccessAttempt model."""

    def it_is_immutable(self) -> None:
        """Verify DatabaseAccessAttempt is frozen/immutable."""
        attempt = DatabaseAccessAttempt(
            library='sqlite3',
            connection_string=':memory:',
            test_nodeid='test::fn',
            allowed=False,
        )

        with pytest.raises(Exception):  # noqa: B017, PT011
            attempt.library = 'other'  # type: ignore[misc]

    def it_stores_all_fields(self) -> None:
        """Verify all fields are stored correctly."""
        attempt = DatabaseAccessAttempt(
            library='psycopg2',
            connection_string='postgresql://localhost/test',
            test_nodeid='tests/test_db.py::test_query',
            allowed=True,
        )

        assert attempt.library == 'psycopg2'
        assert attempt.connection_string == 'postgresql://localhost/test'
        assert attempt.test_nodeid == 'tests/test_db.py::test_query'
        assert attempt.allowed is True

    def it_supports_equality(self) -> None:
        """Verify DatabaseAccessAttempt supports equality comparison."""
        attempt1 = DatabaseAccessAttempt(
            library='sqlite3',
            connection_string=':memory:',
            test_nodeid='test::fn',
            allowed=False,
        )
        attempt2 = DatabaseAccessAttempt(
            library='sqlite3',
            connection_string=':memory:',
            test_nodeid='test::fn',
            allowed=False,
        )

        assert attempt1 == attempt2


@pytest.mark.small
class DescribeDatabasePatchingBlockerBlocking:
    """Tests that verify database calls are blocked for small tests."""

    def it_blocks_sqlite3_connect_for_small_tests(self) -> None:
        """Verify patched sqlite3.connect raises DatabaseViolationError for small tests."""
        import sqlite3

        blocker = DatabasePatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        try:
            with pytest.raises(DatabaseViolationError) as exc_info:
                sqlite3.connect(':memory:')

            assert exc_info.value.library == 'sqlite3'
            assert exc_info.value.connection_string == ':memory:'
        finally:
            blocker.deactivate()

    def it_blocks_sqlite3_connect_with_file_path_for_small_tests(self) -> None:
        """Verify patched sqlite3.connect raises for file paths too."""
        import sqlite3

        blocker = DatabasePatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        try:
            with pytest.raises(DatabaseViolationError) as exc_info:
                sqlite3.connect('/tmp/test.db')

            assert exc_info.value.library == 'sqlite3'
            assert '/tmp/test.db' in exc_info.value.connection_string
        finally:
            blocker.deactivate()


@pytest.mark.medium
class DescribeDatabasePatchingBlockerIntegration:
    """Integration tests that actually execute database calls for medium tests."""

    def it_allows_sqlite3_connect_for_medium_tests(self) -> None:
        """Verify patched sqlite3.connect delegates to original for medium tests."""
        import sqlite3

        blocker = DatabasePatchingBlocker()
        blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)

        try:
            conn = sqlite3.connect(':memory:')
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            result = cursor.fetchone()
            conn.close()

            assert result == (1,)
        finally:
            blocker.deactivate()

    def it_allows_sqlite3_connect_for_large_tests(self) -> None:
        """Verify patched sqlite3.connect delegates to original for large tests."""
        import sqlite3

        blocker = DatabasePatchingBlocker()
        blocker.activate(TestSize.LARGE, EnforcementMode.STRICT)

        try:
            conn = sqlite3.connect(':memory:')
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE test (id INTEGER)')
            cursor.execute('INSERT INTO test VALUES (42)')
            cursor.execute('SELECT * FROM test')
            result = cursor.fetchone()
            conn.close()

            assert result == (42,)
        finally:
            blocker.deactivate()


@pytest.mark.small
class DescribeDatabasePatchingBlockerViolationCallback:
    """Tests for the DatabasePatchingBlocker violation callback feature."""

    def it_calls_violation_callback_on_violation_in_strict_mode(self) -> None:
        """Verify violation callback is invoked when a database violation occurs in STRICT mode."""
        callback_invocations: list[tuple[str, str, str, bool]] = []

        def callback(violation_type: str, test_nodeid: str, details: str, *, failed: bool) -> None:
            callback_invocations.append((violation_type, test_nodeid, details, failed))

        blocker = DatabasePatchingBlocker(violation_callback=callback)
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        try:
            with pytest.raises(DatabaseViolationError):
                blocker.on_violation('sqlite3', ':memory:', 'test_module.py::test_fn')

            assert len(callback_invocations) == 1
            violation_type, test_nodeid, details, failed = callback_invocations[0]
            assert violation_type == 'database'
            assert test_nodeid == 'test_module.py::test_fn'
            assert 'sqlite3' in details
            assert ':memory:' in details
            assert failed is True
        finally:
            blocker.reset()

    def it_calls_violation_callback_on_violation_in_warn_mode(self) -> None:
        """Verify violation callback is invoked when a database violation occurs in WARN mode."""
        callback_invocations: list[tuple[str, str, str, bool]] = []

        def callback(violation_type: str, test_nodeid: str, details: str, *, failed: bool) -> None:
            callback_invocations.append((violation_type, test_nodeid, details, failed))

        blocker = DatabasePatchingBlocker(violation_callback=callback)
        blocker.activate(TestSize.SMALL, EnforcementMode.WARN)

        try:
            blocker.on_violation('psycopg2', 'postgresql://localhost/db', 'test_module.py::test_db')

            assert len(callback_invocations) == 1
            violation_type, test_nodeid, details, failed = callback_invocations[0]
            assert violation_type == 'database'
            assert test_nodeid == 'test_module.py::test_db'
            assert 'psycopg2' in details
            assert 'postgresql://localhost/db' in details
            assert failed is False
        finally:
            blocker.reset()

    def it_does_not_call_callback_when_not_set(self) -> None:
        """Verify no error when violation_callback is None."""
        blocker = DatabasePatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        try:
            with pytest.raises(DatabaseViolationError):
                blocker.on_violation('sqlite3', ':memory:', 'test_module.py::test_fn')
        finally:
            blocker.reset()

    def it_does_not_raise_and_calls_callback_with_failed_false_in_off_mode(self) -> None:
        """Verify OFF mode calls callback with failed=False and does not raise."""
        callback_invocations: list[tuple[str, str, str, bool]] = []

        def callback(violation_type: str, test_nodeid: str, details: str, *, failed: bool) -> None:
            callback_invocations.append((violation_type, test_nodeid, details, failed))

        blocker = DatabasePatchingBlocker(violation_callback=callback)
        blocker.activate(TestSize.SMALL, EnforcementMode.OFF)

        try:
            blocker.on_violation('sqlite3', ':memory:', 'test_mod::test_fn')

            assert len(callback_invocations) == 1
            violation_type, test_nodeid, details, failed = callback_invocations[0]
            assert violation_type == 'database'
            assert test_nodeid == 'test_mod::test_fn'
            assert 'sqlite3' in details
            assert ':memory:' in details
            assert failed is False
        finally:
            blocker.reset()

    def it_does_not_raise_without_callback_in_off_mode(self) -> None:
        """Verify OFF mode does not raise even without a callback attached."""
        blocker = DatabasePatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.OFF)

        try:
            blocker.on_violation('sqlite3', ':memory:', 'test_mod::test_fn')
        finally:
            blocker.reset()


@pytest.mark.small
class DescribeIsCoverageDataFile:
    """Tests for the is_coverage_data_file helper function.

    Each test verifies a distinct path that forces the real basename-matching
    logic rather than a hardcoded return value.  Tests for True and False are
    interleaved so that 'return True' and 'return False' both fail.
    """

    def it_returns_true_for_bare_coverage_file(self) -> None:
        """Bare '.coverage' filename is a coverage data file."""
        assert is_coverage_data_file('.coverage') is True

    def it_returns_true_for_suffixed_coverage_file(self) -> None:
        """'.coverage.host.pid.suffix' filename is a coverage data file."""
        assert is_coverage_data_file('.coverage.myhost.12345.abcdef') is True

    def it_returns_true_for_coverage_file_in_subdirectory(self) -> None:
        """Full path whose basename is '.coverage' is a coverage data file."""
        assert is_coverage_data_file('/path/to/project/.coverage') is True

    def it_returns_true_for_suffixed_coverage_file_in_subdirectory(self) -> None:
        """Full path whose basename starts with '.coverage.' is a coverage data file."""
        assert is_coverage_data_file('/path/to/project/.coverage.myhost.12345.abc') is True

    def it_returns_false_for_memory_database(self) -> None:
        """':memory:' is not a coverage data file."""
        assert is_coverage_data_file(':memory:') is False

    def it_returns_false_for_regular_sqlite_file(self) -> None:
        """A plain .db file is not a coverage data file."""
        assert is_coverage_data_file('/tmp/test.db') is False

    def it_returns_false_for_file_named_coverage_without_dot_prefix(self) -> None:
        """'coverage.db' does not start with '.coverage' — not a coverage file."""
        assert is_coverage_data_file('coverage.db') is False

    def it_returns_false_for_file_with_coverage_in_directory_name(self) -> None:
        """A file whose parent dir contains 'coverage' but whose basename does not match."""
        assert is_coverage_data_file('/coverage/.data/test.db') is False

    def it_returns_false_for_empty_string(self) -> None:
        """An empty string has no basename and is not a coverage data file."""
        assert is_coverage_data_file('') is False


@pytest.mark.small
class DescribeCoverageDataFileExclusion:
    """Tests that coverage.py data files are excluded from database hermeticity checks.

    Coverage.py writes its sqlite3 data to '.coverage' and
    '.coverage.<host>.<pid>.<suffix>' files during test execution.  These must
    not trigger DatabaseViolationError, even for SMALL/STRICT tests.

    The tests alternate between True and False results so that neither
    'return True' nor 'return False' can pass the full class.
    """

    def it_allows_coverage_default_file_for_small_test_with_patching_blocker(self) -> None:
        """DatabasePatchingBlocker allows '.coverage' for SMALL/STRICT tests."""
        blocker = DatabasePatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        try:
            is_connection_allowed = blocker.check_connection_allowed('sqlite3', '.coverage')
        finally:
            blocker.deactivate()

        assert is_connection_allowed is True

    def it_allows_coverage_suffixed_file_for_small_test_with_patching_blocker(self) -> None:
        """DatabasePatchingBlocker allows '.coverage.myhost.12345.abcdef' for SMALL/STRICT."""
        blocker = DatabasePatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        try:
            is_connection_allowed = blocker.check_connection_allowed('sqlite3', '.coverage.myhost.12345.abcdef')
        finally:
            blocker.deactivate()

        assert is_connection_allowed is True

    def it_allows_coverage_file_in_subdirectory_for_small_test_with_patching_blocker(
        self,
    ) -> None:
        """DatabasePatchingBlocker allows a full path to '.coverage.host.pid.suffix'."""
        blocker = DatabasePatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        try:
            is_connection_allowed = blocker.check_connection_allowed(
                'sqlite3',
                '/path/to/project/.coverage.myhost.12345.abc',
            )
        finally:
            blocker.deactivate()

        assert is_connection_allowed is True

    def it_still_blocks_regular_sqlite_for_small_test_with_patching_blocker(self) -> None:
        """DatabasePatchingBlocker still blocks ':memory:' for SMALL/STRICT."""
        blocker = DatabasePatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        try:
            is_connection_allowed = blocker.check_connection_allowed('sqlite3', ':memory:')
        finally:
            blocker.deactivate()

        assert is_connection_allowed is False

    def it_still_blocks_file_sqlite_for_small_test_with_patching_blocker(self) -> None:
        """DatabasePatchingBlocker still blocks '/tmp/test.db' for SMALL/STRICT."""
        blocker = DatabasePatchingBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        try:
            is_connection_allowed = blocker.check_connection_allowed('sqlite3', '/tmp/test.db')
        finally:
            blocker.deactivate()

        assert is_connection_allowed is False

    def it_allows_coverage_default_file_for_small_test_with_fake_blocker(self) -> None:
        """FakeDatabaseBlocker allows '.coverage' for SMALL/STRICT tests."""
        blocker = FakeDatabaseBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        is_connection_allowed = blocker.check_connection_allowed('sqlite3', '.coverage')

        blocker.deactivate()
        assert is_connection_allowed is True
        assert blocker.connection_attempts[-1].allowed is True

    def it_allows_coverage_suffixed_file_for_small_test_with_fake_blocker(self) -> None:
        """FakeDatabaseBlocker allows '.coverage.host.123.abc' for SMALL/STRICT."""
        blocker = FakeDatabaseBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        is_connection_allowed = blocker.check_connection_allowed('sqlite3', '.coverage.host.123.abc')

        blocker.deactivate()
        assert is_connection_allowed is True
        assert blocker.connection_attempts[-1].allowed is True

    def it_still_blocks_regular_sqlite_for_small_test_with_fake_blocker(self) -> None:
        """FakeDatabaseBlocker still blocks ':memory:' for SMALL/STRICT."""
        blocker = FakeDatabaseBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        is_connection_allowed = blocker.check_connection_allowed('sqlite3', ':memory:')

        blocker.deactivate()
        assert is_connection_allowed is False
        assert blocker.connection_attempts[-1].allowed is False
