# Database Testing Patterns

This guide covers patterns for testing database-related code with pytest-test-categories, from small tests using fakes to medium tests with real databases.

## The Testing Pyramid for Databases

Database testing follows the same pyramid as all testing:

| Test Size | Database Approach | Use Case |
|-----------|-------------------|----------|
| Small (80%) | In-memory fakes, mocks | Business logic, repository contracts |
| Medium (15%) | SQLite in-memory, containers | SQL queries, migrations, ORM behavior |
| Large (5%) | Staging database | Full integration, performance |

## Small Tests: Repository Fakes

The most effective way to test database-related code is to abstract the database behind a repository interface and use fakes in tests.

### Define the Repository Interface

```python
# src/repositories.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    id: int | None
    name: str
    email: str
    created_at: datetime | None = None


class UserRepository(ABC):
    """Abstract repository for user persistence."""

    @abstractmethod
    def get_by_id(self, user_id: int) -> User | None:
        """Find user by ID."""

    @abstractmethod
    def get_by_email(self, email: str) -> User | None:
        """Find user by email."""

    @abstractmethod
    def save(self, user: User) -> User:
        """Save user and return with assigned ID."""

    @abstractmethod
    def delete(self, user_id: int) -> bool:
        """Delete user. Returns True if deleted."""

    @abstractmethod
    def list_all(self, limit: int = 100, offset: int = 0) -> list[User]:
        """List users with pagination."""
```

### Create an In-Memory Fake

```python
# tests/fakes/fake_user_repository.py
from datetime import datetime

from repositories import User, UserRepository


class FakeUserRepository(UserRepository):
    """In-memory fake for testing without a database."""

    def __init__(self):
        self._users: dict[int, User] = {}
        self._next_id = 1

    def get_by_id(self, user_id: int) -> User | None:
        return self._users.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    def save(self, user: User) -> User:
        if user.id is None:
            user = User(
                id=self._next_id,
                name=user.name,
                email=user.email,
                created_at=datetime.now(),
            )
            self._next_id += 1
        self._users[user.id] = user
        return user

    def delete(self, user_id: int) -> bool:
        if user_id in self._users:
            del self._users[user_id]
            return True
        return False

    def list_all(self, limit: int = 100, offset: int = 0) -> list[User]:
        users = list(self._users.values())
        return users[offset : offset + limit]

    # Test helpers (not part of interface)
    def add_users(self, *users: User) -> None:
        """Bulk add users for test setup."""
        for user in users:
            self.save(user)

    def clear(self) -> None:
        """Reset repository state."""
        self._users.clear()
        self._next_id = 1
```

### Test with the Fake

```python
import pytest
from datetime import datetime

from repositories import User
from fakes.fake_user_repository import FakeUserRepository


@pytest.fixture
def user_repository():
    """Provide a fresh fake repository for each test."""
    return FakeUserRepository()


@pytest.mark.small
class DescribeUserRepository:
    """Tests for user repository behavior."""

    def test_saves_new_user_with_generated_id(self, user_repository):
        user = User(id=None, name="Alice", email="alice@example.com")

        saved = user_repository.save(user)

        assert saved.id is not None
        assert saved.id > 0
        assert saved.name == "Alice"

    def test_get_by_id_returns_saved_user(self, user_repository):
        user = User(id=None, name="Bob", email="bob@example.com")
        saved = user_repository.save(user)

        retrieved = user_repository.get_by_id(saved.id)

        assert retrieved is not None
        assert retrieved.name == "Bob"

    def test_get_by_id_returns_none_for_unknown(self, user_repository):
        result = user_repository.get_by_id(999)

        assert result is None

    def test_get_by_email_finds_user(self, user_repository):
        user = User(id=None, name="Charlie", email="charlie@example.com")
        user_repository.save(user)

        found = user_repository.get_by_email("charlie@example.com")

        assert found is not None
        assert found.name == "Charlie"

    def test_delete_removes_user(self, user_repository):
        user = User(id=None, name="Dave", email="dave@example.com")
        saved = user_repository.save(user)

        deleted = user_repository.delete(saved.id)

        assert deleted is True
        assert user_repository.get_by_id(saved.id) is None

    def test_delete_returns_false_for_unknown(self, user_repository):
        result = user_repository.delete(999)

        assert result is False

    def test_list_all_returns_all_users(self, user_repository):
        user_repository.add_users(
            User(id=None, name="User1", email="user1@example.com"),
            User(id=None, name="User2", email="user2@example.com"),
            User(id=None, name="User3", email="user3@example.com"),
        )

        users = user_repository.list_all()

        assert len(users) == 3

    def test_list_all_respects_pagination(self, user_repository):
        for i in range(10):
            user_repository.save(User(id=None, name=f"User{i}", email=f"user{i}@example.com"))

        page1 = user_repository.list_all(limit=3, offset=0)
        page2 = user_repository.list_all(limit=3, offset=3)

        assert len(page1) == 3
        assert len(page2) == 3
        assert page1[0].id != page2[0].id
```

### Test Services Using the Repository

```python
# src/user_service.py
from repositories import User, UserRepository


class UserService:
    """Business logic for user operations."""

    def __init__(self, repository: UserRepository):
        self._repository = repository

    def register_user(self, name: str, email: str) -> User:
        """Register a new user, checking for duplicates."""
        existing = self._repository.get_by_email(email)
        if existing:
            raise ValueError(f"Email already registered: {email}")

        user = User(id=None, name=name, email=email)
        return self._repository.save(user)

    def get_user_profile(self, user_id: int) -> dict:
        """Get user profile or raise if not found."""
        user = self._repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "member_since": user.created_at.isoformat() if user.created_at else None,
        }
```

```python
# tests/test_user_service.py
import pytest

from user_service import UserService
from fakes.fake_user_repository import FakeUserRepository


@pytest.fixture
def user_service():
    """Provide user service with fake repository."""
    repository = FakeUserRepository()
    return UserService(repository)


@pytest.mark.small
class DescribeUserService:
    """Tests for user service business logic."""

    def test_registers_new_user(self, user_service):
        user = user_service.register_user("Alice", "alice@example.com")

        assert user.id is not None
        assert user.name == "Alice"

    def test_rejects_duplicate_email(self, user_service):
        user_service.register_user("Alice", "alice@example.com")

        with pytest.raises(ValueError, match="Email already registered"):
            user_service.register_user("Bob", "alice@example.com")

    def test_gets_user_profile(self, user_service):
        user = user_service.register_user("Charlie", "charlie@example.com")

        profile = user_service.get_user_profile(user.id)

        assert profile["name"] == "Charlie"
        assert profile["email"] == "charlie@example.com"

    def test_raises_for_unknown_user(self, user_service):
        with pytest.raises(ValueError, match="User not found"):
            user_service.get_user_profile(999)
```

## Small Tests: SQLite In-Memory

For testing actual SQL queries without a real database server, use SQLite in-memory mode.

```python
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def sqlite_engine():
    """Create in-memory SQLite engine."""
    engine = create_engine("sqlite:///:memory:")
    yield engine
    engine.dispose()


@pytest.fixture
def sqlite_session(sqlite_engine):
    """Create session with initialized schema."""
    # Initialize schema
    with sqlite_engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()

    Session = sessionmaker(bind=sqlite_engine)
    session = Session()
    yield session
    session.close()


@pytest.mark.small
def test_inserts_user(sqlite_session):
    """Test SQL insert with in-memory SQLite."""
    sqlite_session.execute(
        text("INSERT INTO users (name, email) VALUES (:name, :email)"),
        {"name": "Alice", "email": "alice@example.com"},
    )
    sqlite_session.commit()

    result = sqlite_session.execute(text("SELECT name FROM users WHERE email = :email"), {"email": "alice@example.com"})
    name = result.scalar()

    assert name == "Alice"


@pytest.mark.small
def test_enforces_unique_email(sqlite_session):
    """Test unique constraint with in-memory SQLite."""
    from sqlalchemy.exc import IntegrityError

    sqlite_session.execute(
        text("INSERT INTO users (name, email) VALUES (:name, :email)"),
        {"name": "Alice", "email": "alice@example.com"},
    )
    sqlite_session.commit()

    with pytest.raises(IntegrityError):
        sqlite_session.execute(
            text("INSERT INTO users (name, email) VALUES (:name, :email)"),
            {"name": "Bob", "email": "alice@example.com"},
        )
        sqlite_session.commit()
```

### SQLite Limitations

SQLite differs from PostgreSQL/MySQL in several ways:

- No `SERIAL` type (use `INTEGER PRIMARY KEY AUTOINCREMENT`)
- Limited constraint enforcement
- No stored procedures
- Different date/time handling

For PostgreSQL-specific features, use medium tests with containers.

## Medium Tests: pytest-postgresql

[pytest-postgresql](https://pypi.org/project/pytest-postgresql/) provides fixtures for PostgreSQL testing.

### Installation

```bash
pip install pytest-postgresql psycopg2-binary
# or
uv add --dev pytest-postgresql psycopg2-binary
```

### Basic Usage

```python
import pytest


@pytest.mark.medium
def test_with_postgresql(postgresql):
    """Test with real PostgreSQL using pytest-postgresql."""
    cursor = postgresql.cursor()

    cursor.execute("""
        CREATE TABLE products (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            price DECIMAL(10, 2)
        )
    """)
    cursor.execute(
        "INSERT INTO products (name, price) VALUES (%s, %s) RETURNING id",
        ("Widget", 19.99),
    )
    product_id = cursor.fetchone()[0]
    postgresql.commit()

    cursor.execute("SELECT name, price FROM products WHERE id = %s", (product_id,))
    name, price = cursor.fetchone()

    assert name == "Widget"
    assert float(price) == 19.99
```

### With SQLAlchemy ORM

```python
import pytest
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)


@pytest.fixture
def sqlalchemy_session(postgresql):
    """Create SQLAlchemy session connected to test PostgreSQL."""
    connection_string = (
        f"postgresql://{postgresql.info.user}:"
        f"@{postgresql.info.host}:{postgresql.info.port}"
        f"/{postgresql.info.dbname}"
    )
    engine = create_engine(connection_string)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.mark.medium
def test_orm_operations(sqlalchemy_session):
    """Test SQLAlchemy ORM with real PostgreSQL."""
    user = UserModel(name="Alice", email="alice@example.com")
    sqlalchemy_session.add(user)
    sqlalchemy_session.commit()

    retrieved = sqlalchemy_session.query(UserModel).filter_by(email="alice@example.com").first()

    assert retrieved is not None
    assert retrieved.name == "Alice"
    assert retrieved.id is not None
```

## Medium Tests: Testcontainers

For more control over database containers, use testcontainers (see [Container Testing](container-testing.md)).

```python
import pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy import create_engine, text


@pytest.fixture(scope="module")
def postgres_container():
    """Start PostgreSQL container for the test module."""
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres


@pytest.fixture
def db_engine(postgres_container):
    """Create engine connected to container."""
    engine = create_engine(postgres_container.get_connection_url())
    yield engine
    engine.dispose()


@pytest.mark.medium
def test_postgres_specific_features(db_engine):
    """Test PostgreSQL-specific features."""
    with db_engine.connect() as conn:
        # Test JSONB (PostgreSQL-specific)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS events (
                id SERIAL PRIMARY KEY,
                data JSONB NOT NULL
            )
        """))
        conn.execute(
            text("INSERT INTO events (data) VALUES (:data)"),
            {"data": '{"type": "click", "button": "submit"}'},
        )
        conn.commit()

        # Query JSONB
        result = conn.execute(text("SELECT data->>'type' FROM events"))
        event_type = result.scalar()

        assert event_type == "click"
```

## Fixture Patterns

### Transaction Rollback Pattern

Use transactions to isolate tests without recreating tables:

```python
@pytest.fixture(scope="module")
def db_engine(postgres_container):
    """Engine shared across module."""
    engine = create_engine(postgres_container.get_connection_url())

    # Create schema once
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                email VARCHAR(255) UNIQUE
            )
        """))
        conn.commit()

    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """Session with automatic rollback."""
    connection = db_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()  # Undo all changes
    connection.close()


@pytest.mark.medium
def test_creates_user(db_session):
    """Changes are rolled back after test."""
    db_session.execute(
        text("INSERT INTO users (name, email) VALUES (:name, :email)"),
        {"name": "Test", "email": "test@example.com"},
    )

    # This data won't persist to other tests


@pytest.mark.medium
def test_table_is_empty(db_session):
    """Previous test's data was rolled back."""
    result = db_session.execute(text("SELECT COUNT(*) FROM users"))
    count = result.scalar()

    assert count == 0
```

### Factory Fixtures

```python
@pytest.fixture
def user_factory(db_session):
    """Factory for creating test users."""
    created_ids = []

    def create(name="Test User", email=None):
        if email is None:
            email = f"{name.lower().replace(' ', '.')}@example.com"

        result = db_session.execute(
            text("INSERT INTO users (name, email) VALUES (:name, :email) RETURNING id"),
            {"name": name, "email": email},
        )
        user_id = result.scalar()
        db_session.commit()
        created_ids.append(user_id)
        return user_id

    yield create

    # Cleanup (if not using transaction rollback)
    for user_id in created_ids:
        db_session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
    db_session.commit()


@pytest.mark.medium
def test_with_multiple_users(user_factory, db_session):
    """Create users via factory."""
    alice_id = user_factory("Alice")
    bob_id = user_factory("Bob")

    result = db_session.execute(text("SELECT COUNT(*) FROM users"))
    count = result.scalar()

    assert count == 2
```

## Alembic Migration Testing

Test database migrations with Alembic:

```python
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


@pytest.fixture(scope="module")
def alembic_config(postgres_container):
    """Configure Alembic for test database."""
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", postgres_container.get_connection_url())
    return config


@pytest.mark.medium
def test_migrations_apply_cleanly(alembic_config, postgres_container):
    """Test that all migrations apply without errors."""
    # Apply all migrations
    command.upgrade(alembic_config, "head")

    # Verify expected tables exist
    engine = create_engine(postgres_container.get_connection_url())
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    assert "users" in tables
    assert "orders" in tables
    assert "alembic_version" in tables


@pytest.mark.medium
def test_migrations_are_reversible(alembic_config, postgres_container):
    """Test that migrations can be rolled back."""
    # Apply all
    command.upgrade(alembic_config, "head")

    # Roll back all
    command.downgrade(alembic_config, "base")

    # Verify tables are gone
    engine = create_engine(postgres_container.get_connection_url())
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    assert "users" not in tables
    assert "orders" not in tables
```

## When to Use Each Approach

| Approach | Test Size | Use When |
|----------|-----------|----------|
| Fake repositories | Small | Testing business logic, service layers |
| SQLite in-memory | Small | Testing basic SQL, ORM mappings |
| pytest-postgresql | Medium | Testing PostgreSQL-specific features |
| Testcontainers | Medium | Testing with specific database versions |
| Staging database | Large | Full integration testing |

### Decision Guide

1. **Can you test without SQL?** Use fake repositories (small)
2. **Testing basic SQL/ORM?** Use SQLite in-memory (small)
3. **Need PostgreSQL features?** Use containers (medium)
4. **Testing production parity?** Use staging database (large)

## Best Practices

### 1. Prefer Fakes Over Mocks

Fakes implement the real interface; mocks just record calls. Fakes catch more bugs:

```python
# Good: Fake implements real behavior
class FakeUserRepository(UserRepository):
    def get_by_email(self, email: str) -> User | None:
        for user in self._users.values():
            if user.email == email:
                return user
        return None

# Less good: Mock just returns configured value
mock_repo = mocker.Mock()
mock_repo.get_by_email.return_value = User(...)
```

### 2. Test Repository Contracts

Ensure fakes and real implementations behave identically:

```python
class RepositoryContractTests:
    """Contract tests that both fake and real implementations must pass."""

    @pytest.fixture
    def repository(self):
        raise NotImplementedError

    def test_save_assigns_id(self, repository):
        user = User(id=None, name="Test", email="test@example.com")
        saved = repository.save(user)
        assert saved.id is not None

    def test_get_returns_saved_user(self, repository):
        user = User(id=None, name="Test", email="test@example.com")
        saved = repository.save(user)
        retrieved = repository.get_by_id(saved.id)
        assert retrieved.name == saved.name


class TestFakeRepository(RepositoryContractTests):
    @pytest.fixture
    def repository(self):
        return FakeUserRepository()


@pytest.mark.medium
class TestRealRepository(RepositoryContractTests):
    @pytest.fixture
    def repository(self, postgres_container):
        return PostgresUserRepository(postgres_container.get_connection_url())
```

### 3. Isolate Test Data

Each test should create its own data, not rely on pre-existing data:

```python
# Good: Test creates its own data
def test_finds_user_by_email(user_repository):
    user = user_repository.save(User(id=None, name="Alice", email="alice@example.com"))

    found = user_repository.get_by_email("alice@example.com")

    assert found.id == user.id

# Bad: Test relies on data from other tests
def test_finds_existing_user(user_repository):
    # Assumes "alice@example.com" exists from another test
    found = user_repository.get_by_email("alice@example.com")
    assert found is not None
```

## Related Documentation

- [Container Testing](container-testing.md) - Testcontainers in depth
- [Common Patterns](common-patterns.md) - Repository and fake patterns
- [Network Isolation](network-isolation.md) - Database connection isolation
