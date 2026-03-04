"""Optional database library patching for DatabasePatchingBlocker.

This module handles patching and restoring optional database libraries
(psycopg2, psycopg, pymysql, pymongo, redis, sqlalchemy) that may or may
not be installed in the current environment.

Separating this code from the core sqlite3 patching in database.py reflects
that the two halves change for different reasons:
- Core sqlite3 logic changes when enforcement semantics change.
- Optional-library code changes when a new library needs support.

The public interface is two functions:

    patch_optional_libraries(blocker)
    restore_optional_libraries(blocker)

Neither function imports DatabasePatchingBlocker at runtime; the TYPE_CHECKING
guard prevents a circular import while preserving static-analysis support.

"""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_test_categories.adapters.database import DatabasePatchingBlocker


def patch_optional_libraries(blocker: DatabasePatchingBlocker) -> None:
    """Attempt to patch each optional library. Skip libraries not installed.

    Args:
        blocker: The active DatabasePatchingBlocker that intercepts connections.

    """
    # Try to patch psycopg2 (PostgreSQL)
    try:  # pragma: no cover
        import psycopg2  # noqa: PLC0415

        object.__setattr__(blocker, '_original_psycopg2_connect', psycopg2.connect)
        psycopg2.connect = _create_patched_generic_connect(blocker, 'psycopg2', psycopg2.connect)
    except ImportError:
        pass

    # Try to patch psycopg (PostgreSQL 3.x)
    try:  # pragma: no cover
        import psycopg  # noqa: PLC0415

        object.__setattr__(blocker, '_original_psycopg_connect', psycopg.connect)
        psycopg.connect = _create_patched_generic_connect(blocker, 'psycopg', psycopg.connect)  # type: ignore[method-assign]
    except ImportError:
        pass

    # Try to patch pymysql (MySQL)
    try:  # pragma: no cover
        import pymysql  # noqa: PLC0415

        object.__setattr__(blocker, '_original_pymysql_connect', pymysql.connect)
        pymysql.connect = _create_patched_generic_connect(blocker, 'pymysql', pymysql.connect)
    except ImportError:
        pass

    # Try to patch pymongo (MongoDB)
    try:  # pragma: no cover
        import pymongo  # noqa: PLC0415

        object.__setattr__(blocker, '_original_pymongo_client', pymongo.MongoClient)
        pymongo.MongoClient = _create_patched_mongo_client(blocker, pymongo.MongoClient)  # type: ignore[misc]
    except ImportError:
        pass

    # Try to patch redis
    try:  # pragma: no cover
        import redis as redis_module  # noqa: PLC0415

        object.__setattr__(blocker, '_original_redis_redis', redis_module.Redis)
        object.__setattr__(blocker, '_original_redis_strict', redis_module.StrictRedis)
        redis_module.Redis = _create_patched_redis_class(blocker, 'redis.Redis', redis_module.Redis)  # type: ignore[misc]
        redis_module.StrictRedis = _create_patched_redis_class(blocker, 'redis.StrictRedis', redis_module.StrictRedis)  # type: ignore[misc]
    except ImportError:
        pass

    # Try to patch sqlalchemy
    try:  # pragma: no cover
        import sqlalchemy  # noqa: PLC0415

        object.__setattr__(blocker, '_original_sqlalchemy_engine', sqlalchemy.create_engine)
        sqlalchemy.create_engine = _create_patched_sqlalchemy_engine(blocker, sqlalchemy.create_engine)  # type: ignore[method-assign]
    except ImportError:
        pass


def restore_optional_libraries(blocker: DatabasePatchingBlocker) -> None:  # pragma: no cover  # noqa: C901, PLR0915
    """Restore each optional library if it was patched.

    Args:
        blocker: The DatabasePatchingBlocker whose saved originals will be restored.

    """
    # Restore psycopg2
    original_psycopg2 = object.__getattribute__(blocker, '_original_psycopg2_connect')
    if original_psycopg2 is not None:
        try:
            import psycopg2  # noqa: PLC0415

            psycopg2.connect = original_psycopg2
        except ImportError:
            pass
        object.__setattr__(blocker, '_original_psycopg2_connect', None)

    # Restore psycopg
    original_psycopg = object.__getattribute__(blocker, '_original_psycopg_connect')
    if original_psycopg is not None:
        try:
            import psycopg  # noqa: PLC0415

            psycopg.connect = original_psycopg  # type: ignore[method-assign]
        except ImportError:
            pass
        object.__setattr__(blocker, '_original_psycopg_connect', None)

    # Restore pymysql
    original_pymysql = object.__getattribute__(blocker, '_original_pymysql_connect')
    if original_pymysql is not None:
        try:
            import pymysql  # noqa: PLC0415

            pymysql.connect = original_pymysql
        except ImportError:
            pass
        object.__setattr__(blocker, '_original_pymysql_connect', None)

    # Restore pymongo
    original_pymongo = object.__getattribute__(blocker, '_original_pymongo_client')
    if original_pymongo is not None:
        try:
            import pymongo  # noqa: PLC0415

            pymongo.MongoClient = original_pymongo  # type: ignore[misc]
        except ImportError:
            pass
        object.__setattr__(blocker, '_original_pymongo_client', None)

    # Restore redis
    original_redis = object.__getattribute__(blocker, '_original_redis_redis')
    original_strict = object.__getattribute__(blocker, '_original_redis_strict')
    if original_redis is not None:
        try:
            import redis as redis_module  # noqa: PLC0415

            redis_module.Redis = original_redis  # type: ignore[misc]
            redis_module.StrictRedis = original_strict  # type: ignore[misc]
        except ImportError:
            pass
        object.__setattr__(blocker, '_original_redis_redis', None)
        object.__setattr__(blocker, '_original_redis_strict', None)

    # Restore sqlalchemy
    original_sqlalchemy = object.__getattribute__(blocker, '_original_sqlalchemy_engine')
    if original_sqlalchemy is not None:
        try:
            import sqlalchemy  # noqa: PLC0415

            sqlalchemy.create_engine = original_sqlalchemy  # type: ignore[method-assign]
        except ImportError:
            pass
        object.__setattr__(blocker, '_original_sqlalchemy_engine', None)


def _create_patched_generic_connect(  # pragma: no cover
    blocker: DatabasePatchingBlocker,
    library: str,
    original_connect: Callable[..., Any],
) -> Callable[..., Any]:
    """Create a wrapper for generic connect functions.

    Args:
        blocker: The active DatabasePatchingBlocker.
        library: The database library name.
        original_connect: The original connect function.

    Returns:
        A wrapper function that checks permissions before delegating.

    """

    def patched_connect(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        connection_string = str(args[0]) if args else str(kwargs)

        if not blocker._do_check_connection_allowed(library, connection_string):  # noqa: SLF001
            blocker._do_on_violation(library, connection_string, blocker.current_test_nodeid)  # noqa: SLF001

        return original_connect(*args, **kwargs)

    return patched_connect


def _create_patched_mongo_client(  # pragma: no cover
    blocker: DatabasePatchingBlocker,
    original_client: type[Any],
) -> type[Any]:
    """Create a patched MongoDB client class.

    Args:
        blocker: The active DatabasePatchingBlocker.
        original_client: The original MongoClient class.

    Returns:
        A patched class that checks permissions before connecting.

    """

    class PatchedMongoClient(original_client):  # type: ignore[valid-type,misc]
        def __init__(self, host: str | None = None, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
            connection_string = host or 'localhost'

            if not blocker._do_check_connection_allowed('pymongo', connection_string):  # noqa: SLF001
                blocker._do_on_violation('pymongo', connection_string, blocker.current_test_nodeid)  # noqa: SLF001

            super().__init__(host, *args, **kwargs)

    return PatchedMongoClient


def _create_patched_redis_class(  # pragma: no cover
    blocker: DatabasePatchingBlocker,
    library: str,
    original_class: type[Any],
) -> type[Any]:
    """Create a patched Redis client class.

    Args:
        blocker: The active DatabasePatchingBlocker.
        library: The library name (e.g., 'redis.Redis').
        original_class: The original Redis class.

    Returns:
        A patched class that checks permissions before connecting.

    """

    class PatchedRedis(original_class):  # type: ignore[valid-type,misc]
        def __init__(self, host: str = 'localhost', *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
            connection_string = f'{host}:{kwargs.get("port", 6379)}'

            if not blocker._do_check_connection_allowed(library, connection_string):  # noqa: SLF001
                blocker._do_on_violation(library, connection_string, blocker.current_test_nodeid)  # noqa: SLF001

            super().__init__(host, *args, **kwargs)

    return PatchedRedis


def _create_patched_sqlalchemy_engine(  # pragma: no cover
    blocker: DatabasePatchingBlocker,
    original_create_engine: Callable[..., Any],
) -> Callable[..., Any]:
    """Create a wrapper for SQLAlchemy create_engine.

    Args:
        blocker: The active DatabasePatchingBlocker.
        original_create_engine: The original create_engine function.

    Returns:
        A wrapper function that checks permissions before creating engine.

    """

    def patched_create_engine(url: Any, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        connection_string = str(url)

        if not blocker._do_check_connection_allowed('sqlalchemy', connection_string):  # noqa: SLF001
            blocker._do_on_violation('sqlalchemy', connection_string, blocker.current_test_nodeid)  # noqa: SLF001

        return original_create_engine(url, *args, **kwargs)

    return patched_create_engine
