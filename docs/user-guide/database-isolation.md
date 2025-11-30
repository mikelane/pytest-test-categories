# Database Isolation for Hermetic Tests

Database isolation is a test enforcement mechanism that prevents small tests from connecting to databases during execution. This ensures tests are **hermetic** and run **entirely in memory** with no external state.

When enabled, the pytest-test-categories plugin intercepts database connection attempts and either blocks them or warns about them, depending on your configuration.

## Why Database Isolation Matters

Tests that connect to databases introduce several problems:

### External State

Databases maintain state outside the test process:

- Data persists between test runs
- Schema changes affect test behavior
- Indexes and statistics change query plans
- Connection pooling introduces shared state

### Non-Determinism

Shared databases cause test interference:

- Tests may see data from other tests
- Parallel execution causes race conditions
- Cleanup failures leave orphaned data
- Sequence/auto-increment values vary

### I/O Overhead

Database connections involve significant I/O:

- Connection establishment (TCP handshake, authentication)
- Query parsing and planning
- Data serialization and deserialization
- Network round trips for each query

### Environment Coupling

Tests become dependent on database availability:

- Database must be running for tests to pass
- Schema must match expected structure
- Configuration (host, port, credentials) varies between environments
- Database version differences cause subtle bugs

## Test Size Restrictions

Database isolation follows Google's test size definitions from "Software Engineering at Google":

| Test Size | Database Access | Rationale |
|-----------|-----------------|-----------|
| Small     | **Blocked** (including `:memory:`) | Must be hermetic, run in memory only |
| Medium    | Allowed         | May use databases for integration tests |
| Large     | Allowed         | May access production-like databases |
| XLarge    | Allowed         | May access real databases |

### Small Tests

Small tests run entirely in memory:

- **Fast**: No database connection overhead
- **Hermetic**: No dependency on database state
- **Deterministic**: Same input always produces same output
- **Parallelizable**: No database contention

Database isolation enforces hermeticity by blocking all database connections in small tests, including in-memory SQLite (`:memory:`).

### Why Block In-Memory SQLite?

You might wonder why `:memory:` SQLite is also blocked for small tests. While it doesn't perform file I/O, it still represents a database usage pattern that:

- Encourages reliance on database behavior in unit tests
- Makes tests slower than pure in-memory data structures
- Creates coupling between business logic and persistence

For true unit tests, use plain Python data structures (dicts, lists, dataclasses) instead.

### Medium, Large, and XLarge Tests

These tests may access databases freely, enabling:

- Repository layer integration tests
- Schema migration tests
- Query performance tests
- Data integrity tests

## How It Works

The plugin intercepts database connections by patching database library connection functions:

### Patched Entry Points

The following database entry points are intercepted:

**Always patched (standard library):**
- `sqlite3.connect` - SQLite database connections

**Patched if installed:**
- `psycopg2.connect` / `psycopg.connect` - PostgreSQL
- `pymysql.connect` - MySQL
- `pymongo.MongoClient` - MongoDB
- `redis.Redis` / `redis.StrictRedis` - Redis
- `sqlalchemy.create_engine` - SQLAlchemy ORM

### Connection Interception

When a test attempts to connect:

1. The blocker intercepts the connection call
2. It extracts the library name and connection string
3. It checks if the connection is allowed based on test size
4. For violations, it either raises an exception (STRICT) or warns (WARN)

## Enabling Database Isolation

Database isolation is controlled by the `test_categories_enforcement` configuration option.

### Configuration via pyproject.toml

```toml
[tool.pytest.ini_options]
# Enable database isolation enforcement
test_categories_enforcement = "strict"
```

### Configuration via pytest.ini

```ini
[pytest]
test_categories_enforcement = strict
```

### Configuration via Command Line

```bash
pytest --test-categories-enforcement=strict
```

## Enforcement Modes

The plugin supports three enforcement modes:

### STRICT Mode

```toml
test_categories_enforcement = "strict"
```

In strict mode, database violations immediately fail the test with a detailed error message:

```
[TC004] Database Connection Violation
Test: tests/test_repos.py::test_user_repository
Category: SMALL

What happened:
  Attempted sqlite3 database connection to: :memory:

How to fix:
  1. Mock sqlite3.connect using pytest-mock (mocker.patch)
  2. Use dependency injection to provide a fake database/repository
  3. Use in-memory data structures (dict, list) for test data
  4. Test business logic separately from database operations
  5. Change test category to @pytest.mark.medium (if database access is required)

Documentation: https://pytest-test-categories.readthedocs.io/errors/TC004
```

Use strict mode in CI pipelines to catch violations before merge.

### WARN Mode

```toml
test_categories_enforcement = "warn"
```

In warn mode, database violations emit a warning but allow the test to continue:

```
PytestWarning: Database connection violation in test_user_repository:
attempted sqlite3.connect: :memory:
```

Use warn mode during migration to identify violations without breaking the build.

### OFF Mode

```toml
test_categories_enforcement = "off"
```

In off mode, database isolation is disabled entirely.

## Common Remediation Strategies

### 1. Use In-Memory Data Structures

Replace databases with simple Python structures:

```python
from dataclasses import dataclass
import pytest

@dataclass
class User:
    id: str
    name: str
    email: str

# Instead of a real repository with database
class FakeUserRepository:
    def __init__(self):
        self._users: dict[str, User] = {}

    def save(self, user: User) -> None:
        self._users[user.id] = user

    def get(self, user_id: str) -> User | None:
        return self._users.get(user_id)

@pytest.mark.small
def test_user_service():
    repo = FakeUserRepository()
    user = User(id="123", name="Alice", email="alice@example.com")
    repo.save(user)

    retrieved = repo.get("123")

    assert retrieved.name == "Alice"
```

### 2. Use Dependency Injection

Design code to accept repository interfaces:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
import pytest

@dataclass
class User:
    id: str
    name: str

class UserRepository(ABC):
    @abstractmethod
    def get(self, user_id: str) -> User | None: ...

    @abstractmethod
    def save(self, user: User) -> None: ...

# Production implementation
class SqlUserRepository(UserRepository):
    def __init__(self, connection):
        self.conn = connection

    def get(self, user_id: str) -> User | None:
        cursor = self.conn.execute(
            "SELECT id, name FROM users WHERE id = ?", (user_id,)
        )
        row = cursor.fetchone()
        return User(id=row[0], name=row[1]) if row else None

    def save(self, user: User) -> None:
        self.conn.execute(
            "INSERT INTO users (id, name) VALUES (?, ?)",
            (user.id, user.name)
        )

# Test implementation
class FakeUserRepository(UserRepository):
    def __init__(self):
        self._users: dict[str, User] = {}

    def get(self, user_id: str) -> User | None:
        return self._users.get(user_id)

    def save(self, user: User) -> None:
        self._users[user.id] = user

# Service that uses repository
class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def create_user(self, name: str) -> User:
        import uuid
        user = User(id=str(uuid.uuid4()), name=name)
        self.repo.save(user)
        return user

# Small test with fake repository
@pytest.mark.small
def test_create_user():
    repo = FakeUserRepository()
    service = UserService(repo)

    user = service.create_user("Alice")

    assert user.name == "Alice"
    assert repo.get(user.id) is not None
```

### 3. Mock Database Connections

Use pytest-mock to intercept database calls:

```python
import pytest

@pytest.mark.small
def test_user_lookup(mocker):
    mock_conn = mocker.MagicMock()
    mock_cursor = mocker.MagicMock()
    mock_conn.execute.return_value = mock_cursor
    mock_cursor.fetchone.return_value = ("123", "Alice")

    mocker.patch("sqlite3.connect", return_value=mock_conn)

    from myapp.repos import get_user
    user = get_user("123")

    assert user.name == "Alice"
```

### 4. Test Business Logic Separately

Separate business logic from persistence:

```python
from dataclasses import dataclass
import pytest

@dataclass
class Order:
    items: list[str]
    subtotal: float
    tax: float
    total: float

# Pure business logic - no database
def calculate_order_totals(items: list[str], prices: dict[str, float], tax_rate: float) -> Order:
    subtotal = sum(prices.get(item, 0) for item in items)
    tax = subtotal * tax_rate
    total = subtotal + tax
    return Order(items=items, subtotal=subtotal, tax=tax, total=total)

# Small test for pure logic
@pytest.mark.small
def test_calculate_order_totals():
    prices = {"apple": 1.00, "banana": 0.50}

    order = calculate_order_totals(
        items=["apple", "banana"],
        prices=prices,
        tax_rate=0.10,
    )

    assert order.subtotal == 1.50
    assert order.tax == 0.15
    assert order.total == 1.65
```

### 5. Use Fixtures for Medium Tests

Create database fixtures for integration testing:

```python
import sqlite3
import pytest

@pytest.fixture
def db_connection():
    """Create an in-memory SQLite database for medium tests."""
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL
        )
    """)
    yield conn
    conn.close()

@pytest.mark.medium
def test_user_repository_integration(db_connection):
    from myapp.repos import SqlUserRepository, User

    repo = SqlUserRepository(db_connection)
    user = User(id="123", name="Alice", email="alice@example.com")

    repo.save(user)
    retrieved = repo.get("123")

    assert retrieved.name == "Alice"
```

### 6. Use Docker Containers for Real Databases

For production-like integration tests:

```python
import pytest

@pytest.fixture(scope="session")
def postgres_container():
    """Start a PostgreSQL container for integration tests."""
    import docker
    client = docker.from_env()
    container = client.containers.run(
        "postgres:15",
        detach=True,
        ports={"5432/tcp": None},
        environment={
            "POSTGRES_PASSWORD": "test",
            "POSTGRES_DB": "testdb",
        },
    )
    # Wait for postgres to be ready
    import time
    time.sleep(2)

    port = container.ports["5432/tcp"][0]["HostPort"]
    yield f"postgresql://postgres:test@localhost:{port}/testdb"

    container.stop()
    container.remove()

@pytest.mark.medium
def test_postgres_integration(postgres_container):
    import psycopg2
    conn = psycopg2.connect(postgres_container)
    # Test with real PostgreSQL
    ...
```

### 7. Change Test Size

If the test legitimately requires database access:

```python
import pytest

@pytest.mark.medium  # Medium tests can access databases
def test_database_migration(db_connection):
    from myapp.migrations import apply_migrations
    apply_migrations(db_connection)

    # Verify schema
    cursor = db_connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )
    tables = {row[0] for row in cursor.fetchall()}
    assert "users" in tables
```

## Best Practices

### 1. Start with WARN Mode

When first enabling database isolation, use warn mode to identify all violations:

```bash
pytest --test-categories-enforcement=warn 2>&1 | grep "Database connection violation"
```

### 2. Use the Repository Pattern

Separate data access from business logic:

```
+------------------+     +-------------------+     +----------+
|  Business Logic  | --> |    Repository     | --> | Database |
|  (Small Tests)   |     |   (Interface)     |     |          |
+------------------+     +-------------------+     +----------+
                                 ^
                                 |
                         +-------+-------+
                         |               |
                   +-----+-----+   +-----+-----+
                   |   Fake    |   |   Real    |
                   | Repository|   | Repository|
                   | (Tests)   |   | (Prod)    |
                   +-----------+   +-----------+
```

### 3. Use Factories for Test Data

Create test data without database:

```python
from dataclasses import dataclass, field
import uuid

@dataclass
class User:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Test User"
    email: str = "test@example.com"

# Easy to create test data
def test_user_email_validation():
    user = User(email="invalid")
    assert not is_valid_email(user.email)
```

### 4. Test Queries Separately

If you need to test SQL queries, do it in medium tests:

```python
import pytest

# Small test: Test query building logic
@pytest.mark.small
def test_build_search_query():
    from myapp.queries import build_user_search_query

    query, params = build_user_search_query(name="Alice", active=True)

    assert "WHERE" in query
    assert "name LIKE ?" in query
    assert "active = ?" in query
    assert params == ("%Alice%", True)

# Medium test: Test query execution
@pytest.mark.medium
def test_execute_search_query(db_connection):
    # Seed data
    db_connection.execute("INSERT INTO users VALUES ('1', 'Alice', 1)")

    from myapp.repos import search_users
    results = search_users(db_connection, name="Alice")

    assert len(results) == 1
```

## Troubleshooting

### "DatabaseViolationError" for :memory: SQLite

Even in-memory SQLite is blocked for small tests. This is intentional - use Python data structures instead.

**Solution**: Use dicts, lists, or dataclasses for test data.

### "psycopg2.connect not being blocked"

Ensure the library is installed in your test environment. The plugin only patches libraries that are available.

### "SQLAlchemy create_engine not blocked"

SQLAlchemy's `create_engine` is lazy - it doesn't connect until you actually execute a query. The connection happens when:
- You call `engine.connect()`
- You execute a query
- You create a session that executes queries

The plugin intercepts the underlying database connection, not `create_engine`.

### "Tests pass locally but fail in CI"

Common causes:
1. Different database versions
2. Schema differences
3. Missing migrations
4. Environment variable configuration

**Solution**: Use containerized databases with pinned versions for CI.

## Related Documentation

- [Architecture Decision Record: Database Isolation](../architecture/adr-004-database-isolation.md)
- [Test Sizes](test-sizes.md)
- [Network Isolation](network-isolation.md)
- [Filesystem Isolation](filesystem-isolation.md)
- [Configuration Reference](../configuration.md)
