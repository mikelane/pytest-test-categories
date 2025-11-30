"""Production database blocker adapter using patching.

This module provides the production implementation of DatabaseBlockerPort that
actually intercepts database connections by patching connect functions from
database libraries.

The DatabasePatchingBlocker follows hexagonal architecture principles:
- Implements the DatabaseBlockerPort interface (port)
- Patches database connection functions to intercept access attempts
- Raises DatabaseViolationError on unauthorized access
- Restores original functions on deactivation

Patched Libraries:
- sqlite3.connect (standard library, always available)

Optional libraries (patched only if installed):
- psycopg2.connect / psycopg.connect (PostgreSQL)
- pymysql.connect (MySQL)
- pymongo.MongoClient (MongoDB)
- redis.Redis / redis.StrictRedis (Redis)
- sqlalchemy.create_engine (SQLAlchemy)

Example:
    >>> blocker = DatabasePatchingBlocker()
    >>> try:
    ...     blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
    ...     # Any database connection will now be intercepted
    ... finally:
    ...     blocker.deactivate()  # Restore original database behavior

See Also:
    - DatabaseBlockerPort: The abstract interface in ports/database.py
    - FakeDatabaseBlocker: Test adapter in adapters/fake_database.py
    - SocketPatchingNetworkBlocker: Similar production adapter pattern for network

"""

from __future__ import annotations

import sqlite3
from typing import (
    TYPE_CHECKING,
    Any,
)

from pydantic import Field

from pytest_test_categories.exceptions import DatabaseViolationError
from pytest_test_categories.ports.database import DatabaseBlockerPort
from pytest_test_categories.ports.network import EnforcementMode
from pytest_test_categories.types import TestSize

if TYPE_CHECKING:
    from collections.abc import Callable


class DatabasePatchingBlocker(DatabaseBlockerPort):
    """Production adapter that patches database connection functions to block access.

    This adapter intercepts database access by patching:
    - sqlite3.connect (standard library)
    - Optional: psycopg2.connect, psycopg.connect, pymysql.connect, etc.

    The patching is reversible - deactivate() restores the original functions.

    Attributes:
        state: Current blocker state (inherited from DatabaseBlockerPort).
        current_test_size: The test size set during activation.
        current_enforcement_mode: The enforcement mode set during activation.
        current_test_nodeid: The pytest node ID of the current test.

    Warning:
        This adapter modifies global state (database connection functions).
        Always use in a try/finally block or context manager to ensure cleanup.

    Example:
        >>> blocker = DatabasePatchingBlocker()
        >>> try:
        ...     blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        ...     sqlite3.connect(':memory:')  # Raises DatabaseViolationError
        ... finally:
        ...     blocker.deactivate()

    """

    current_test_size: TestSize | None = Field(default=None, description='Test size')
    current_enforcement_mode: EnforcementMode | None = Field(default=None, description='Enforcement mode')
    current_test_nodeid: str = Field(default='', description='Test node ID')

    def model_post_init(self, context: object, /) -> None:  # noqa: ARG002
        """Initialize post-Pydantic setup, storing references to original functions."""
        object.__setattr__(self, '_original_sqlite3_connect', None)
        # Placeholders for optional libraries
        object.__setattr__(self, '_original_psycopg2_connect', None)
        object.__setattr__(self, '_original_psycopg_connect', None)
        object.__setattr__(self, '_original_pymysql_connect', None)
        object.__setattr__(self, '_original_pymongo_client', None)
        object.__setattr__(self, '_original_redis_redis', None)
        object.__setattr__(self, '_original_redis_strict', None)
        object.__setattr__(self, '_original_sqlalchemy_engine', None)

    def _do_activate(
        self,
        test_size: TestSize,
        enforcement_mode: EnforcementMode,
    ) -> None:
        """Install database connection wrappers to intercept connections.

        Installs wrapper functions that intercept database connection attempts
        and check them against the test size restrictions.

        Args:
            test_size: The size category of the current test.
            enforcement_mode: How to handle violations.

        """
        self.current_test_size = test_size
        self.current_enforcement_mode = enforcement_mode

        # Always patch sqlite3 (standard library)
        object.__setattr__(self, '_original_sqlite3_connect', sqlite3.connect)
        sqlite3.connect = self._create_patched_sqlite3_connect()  # type: ignore[method-assign]

        # Optionally patch other libraries if installed
        self._patch_optional_libraries()

    def _do_deactivate(self) -> None:
        """Restore the original database connection functions.

        Restores all original connection functions that were saved during activation.

        """
        # Restore sqlite3
        original_sqlite3 = object.__getattribute__(self, '_original_sqlite3_connect')
        if original_sqlite3 is not None:
            sqlite3.connect = original_sqlite3  # type: ignore[method-assign]

        # Restore optional libraries
        self._restore_optional_libraries()

    def _do_check_connection_allowed(self, library: str, connection_string: str) -> bool:  # noqa: ARG002
        """Check if database connection is allowed by test size rules.

        Rules applied:
        - SMALL: Block all database connections
        - MEDIUM/LARGE/XLARGE: Allow all database connections

        Args:
            library: The database library name.
            connection_string: The connection string or database path.

        Returns:
            True if the connection is allowed, False if it should be blocked.

        """
        return self.current_test_size != TestSize.SMALL

    def _do_on_violation(
        self,
        library: str,
        connection_string: str,
        test_nodeid: str,
    ) -> None:
        """Handle a database access violation based on enforcement mode.

        Behavior:
        - STRICT: Record violation and raise DatabaseViolationError
        - WARN: Record violation, allow connection to proceed
        - OFF: Do nothing

        Args:
            library: The database library name.
            connection_string: The connection string or database path.
            test_nodeid: The pytest node ID of the violating test.

        Raises:
            DatabaseViolationError: If enforcement mode is STRICT.

        """
        is_strict = self.current_enforcement_mode == EnforcementMode.STRICT
        details = f'Attempted {library} connection: {connection_string}'

        # Record violation via callback if set
        if self.violation_callback is not None:
            callback = self.violation_callback
            if callable(callback):
                callback('database', test_nodeid, details, failed=is_strict)

        if is_strict:
            raise DatabaseViolationError(
                test_size=self.current_test_size,  # type: ignore[arg-type]
                test_nodeid=test_nodeid,
                library=library,
                connection_string=connection_string,
            )

    def reset(self) -> None:
        """Reset blocker to initial state, restoring original database functions.

        This is safe to call regardless of current state.

        """
        # Restore sqlite3
        original_sqlite3 = object.__getattribute__(self, '_original_sqlite3_connect')
        if original_sqlite3 is not None:
            sqlite3.connect = original_sqlite3  # type: ignore[method-assign]
            object.__setattr__(self, '_original_sqlite3_connect', None)

        # Restore optional libraries
        self._restore_optional_libraries()

        super().reset()
        self.current_test_size = None
        self.current_enforcement_mode = None
        self.current_test_nodeid = ''

    def _create_patched_sqlite3_connect(self) -> Callable[..., sqlite3.Connection]:
        """Create a wrapper for sqlite3.connect that intercepts connections.

        Returns:
            A wrapper function that checks permissions before delegating to real connect.

        """
        blocker = self
        original_connect = object.__getattribute__(self, '_original_sqlite3_connect')

        def patched_connect(
            database: str,
            *args: Any,  # noqa: ANN401
            **kwargs: Any,  # noqa: ANN401
        ) -> sqlite3.Connection:
            """Check database access permissions before connecting.

            Args:
                database: The database path or ':memory:'.
                *args: Additional positional arguments for connect().
                **kwargs: Additional keyword arguments for connect().

            Returns:
                A database connection if access is allowed.

            Raises:
                DatabaseViolationError: If access is not allowed
                    and enforcement mode is STRICT.

            """
            if not blocker._do_check_connection_allowed('sqlite3', database):  # noqa: SLF001
                blocker._do_on_violation('sqlite3', database, blocker.current_test_nodeid)  # noqa: SLF001

            return original_connect(database, *args, **kwargs)

        return patched_connect

    def _patch_optional_libraries(self) -> None:
        """Patch optional database libraries if they are installed.

        This method attempts to import and patch various database libraries.
        If a library is not installed, the import will fail silently and
        that library will not be patched.

        """
        # Try to patch psycopg2 (PostgreSQL)
        try:  # pragma: no cover
            import psycopg2  # noqa: PLC0415

            object.__setattr__(self, '_original_psycopg2_connect', psycopg2.connect)
            psycopg2.connect = self._create_patched_generic_connect('psycopg2', psycopg2.connect)
        except ImportError:
            pass

        # Try to patch psycopg (PostgreSQL 3.x)
        try:  # pragma: no cover
            import psycopg  # noqa: PLC0415

            object.__setattr__(self, '_original_psycopg_connect', psycopg.connect)
            psycopg.connect = self._create_patched_generic_connect('psycopg', psycopg.connect)  # type: ignore[method-assign]
        except ImportError:
            pass

        # Try to patch pymysql (MySQL)
        try:  # pragma: no cover
            import pymysql  # noqa: PLC0415

            object.__setattr__(self, '_original_pymysql_connect', pymysql.connect)
            pymysql.connect = self._create_patched_generic_connect('pymysql', pymysql.connect)
        except ImportError:
            pass

        # Try to patch pymongo (MongoDB)
        try:  # pragma: no cover
            import pymongo  # noqa: PLC0415

            object.__setattr__(self, '_original_pymongo_client', pymongo.MongoClient)
            pymongo.MongoClient = self._create_patched_mongo_client(pymongo.MongoClient)  # type: ignore[misc]
        except ImportError:
            pass

        # Try to patch redis
        try:  # pragma: no cover
            import redis as redis_module  # noqa: PLC0415

            object.__setattr__(self, '_original_redis_redis', redis_module.Redis)
            object.__setattr__(self, '_original_redis_strict', redis_module.StrictRedis)
            redis_module.Redis = self._create_patched_redis_class('redis.Redis', redis_module.Redis)  # type: ignore[misc]
            redis_module.StrictRedis = self._create_patched_redis_class('redis.StrictRedis', redis_module.StrictRedis)  # type: ignore[misc]
        except ImportError:
            pass

        # Try to patch sqlalchemy
        try:  # pragma: no cover
            import sqlalchemy  # noqa: PLC0415

            object.__setattr__(self, '_original_sqlalchemy_engine', sqlalchemy.create_engine)
            sqlalchemy.create_engine = self._create_patched_sqlalchemy_engine(sqlalchemy.create_engine)  # type: ignore[method-assign]
        except ImportError:
            pass

    def _restore_optional_libraries(self) -> None:  # pragma: no cover
        """Restore optional database libraries to their original state."""
        # Restore psycopg2
        original_psycopg2 = object.__getattribute__(self, '_original_psycopg2_connect')
        if original_psycopg2 is not None:
            try:
                import psycopg2  # noqa: PLC0415

                psycopg2.connect = original_psycopg2
            except ImportError:
                pass
            object.__setattr__(self, '_original_psycopg2_connect', None)

        # Restore psycopg
        original_psycopg = object.__getattribute__(self, '_original_psycopg_connect')
        if original_psycopg is not None:
            try:
                import psycopg  # noqa: PLC0415

                psycopg.connect = original_psycopg  # type: ignore[method-assign]
            except ImportError:
                pass
            object.__setattr__(self, '_original_psycopg_connect', None)

        # Restore pymysql
        original_pymysql = object.__getattribute__(self, '_original_pymysql_connect')
        if original_pymysql is not None:
            try:
                import pymysql  # noqa: PLC0415

                pymysql.connect = original_pymysql
            except ImportError:
                pass
            object.__setattr__(self, '_original_pymysql_connect', None)

        # Restore pymongo
        original_pymongo = object.__getattribute__(self, '_original_pymongo_client')
        if original_pymongo is not None:
            try:
                import pymongo  # noqa: PLC0415

                pymongo.MongoClient = original_pymongo  # type: ignore[misc]
            except ImportError:
                pass
            object.__setattr__(self, '_original_pymongo_client', None)

        # Restore redis
        original_redis = object.__getattribute__(self, '_original_redis_redis')
        original_strict = object.__getattribute__(self, '_original_redis_strict')
        if original_redis is not None:
            try:
                import redis as redis_module  # noqa: PLC0415

                redis_module.Redis = original_redis  # type: ignore[misc]
                redis_module.StrictRedis = original_strict  # type: ignore[misc]
            except ImportError:
                pass
            object.__setattr__(self, '_original_redis_redis', None)
            object.__setattr__(self, '_original_redis_strict', None)

        # Restore sqlalchemy
        original_sqlalchemy = object.__getattribute__(self, '_original_sqlalchemy_engine')
        if original_sqlalchemy is not None:
            try:
                import sqlalchemy  # noqa: PLC0415

                sqlalchemy.create_engine = original_sqlalchemy  # type: ignore[method-assign]
            except ImportError:
                pass
            object.__setattr__(self, '_original_sqlalchemy_engine', None)

    def _create_patched_generic_connect(  # pragma: no cover
        self,
        library: str,
        original_connect: Callable[..., Any],
    ) -> Callable[..., Any]:
        """Create a wrapper for generic connect functions.

        Args:
            library: The database library name.
            original_connect: The original connect function.

        Returns:
            A wrapper function that checks permissions before delegating.

        """
        blocker = self

        def patched_connect(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            connection_string = str(args[0]) if args else str(kwargs)

            if not blocker._do_check_connection_allowed(library, connection_string):  # noqa: SLF001
                blocker._do_on_violation(library, connection_string, blocker.current_test_nodeid)  # noqa: SLF001

            return original_connect(*args, **kwargs)

        return patched_connect

    def _create_patched_mongo_client(  # pragma: no cover
        self,
        original_client: type[Any],
    ) -> type[Any]:
        """Create a patched MongoDB client class.

        Args:
            original_client: The original MongoClient class.

        Returns:
            A patched class that checks permissions before connecting.

        """
        blocker = self

        class PatchedMongoClient(original_client):  # type: ignore[valid-type,misc]
            def __init__(self, host: str | None = None, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
                connection_string = host or 'localhost'

                if not blocker._do_check_connection_allowed('pymongo', connection_string):  # noqa: SLF001
                    blocker._do_on_violation('pymongo', connection_string, blocker.current_test_nodeid)  # noqa: SLF001

                super().__init__(host, *args, **kwargs)

        return PatchedMongoClient

    def _create_patched_redis_class(  # pragma: no cover
        self,
        library: str,
        original_class: type[Any],
    ) -> type[Any]:
        """Create a patched Redis client class.

        Args:
            library: The library name (e.g., 'redis.Redis').
            original_class: The original Redis class.

        Returns:
            A patched class that checks permissions before connecting.

        """
        blocker = self

        class PatchedRedis(original_class):  # type: ignore[valid-type,misc]
            def __init__(self, host: str = 'localhost', *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
                connection_string = f'{host}:{kwargs.get("port", 6379)}'

                if not blocker._do_check_connection_allowed(library, connection_string):  # noqa: SLF001
                    blocker._do_on_violation(library, connection_string, blocker.current_test_nodeid)  # noqa: SLF001

                super().__init__(host, *args, **kwargs)

        return PatchedRedis

    def _create_patched_sqlalchemy_engine(  # pragma: no cover
        self,
        original_create_engine: Callable[..., Any],
    ) -> Callable[..., Any]:
        """Create a wrapper for SQLAlchemy create_engine.

        Args:
            original_create_engine: The original create_engine function.

        Returns:
            A wrapper function that checks permissions before creating engine.

        """
        blocker = self

        def patched_create_engine(url: Any, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            connection_string = str(url)

            if not blocker._do_check_connection_allowed('sqlalchemy', connection_string):  # noqa: SLF001
                blocker._do_on_violation('sqlalchemy', connection_string, blocker.current_test_nodeid)  # noqa: SLF001

            return original_create_engine(url, *args, **kwargs)

        return patched_create_engine
