# Fixtures Reference

This page documents fixtures and fixture recommendations for pytest-test-categories.

## Plugin-Provided Fixtures

pytest-test-categories does not currently provide any custom fixtures. The plugin operates through pytest hooks rather than fixtures, which allows it to work seamlessly with your existing test infrastructure.

## Recommended Fixture Usage by Test Size

Different test sizes have different fixture scope recommendations based on their characteristics and isolation requirements.

### Small Tests

Small tests should use narrow-scoped fixtures with minimal setup:

| Fixture Scope | Recommendation |
|--------------|----------------|
| `function` | Preferred - provides isolation between tests |
| `class` | Acceptable for sharing test doubles |
| `module` | Use sparingly - only for immutable data |
| `session` | Avoid - breaks test isolation |

**Recommended Fixtures:**

```python
import pytest

@pytest.fixture
def mock_api_client(mocker):
    """Mock API client for small tests."""
    return mocker.Mock(spec=APIClient)

@pytest.fixture
def sample_user():
    """Immutable test data."""
    return User(id=1, name="Test User", email="test@example.com")
```

**Allowed pytest Built-in Fixtures:**

| Fixture | Description | Why Allowed |
|---------|-------------|-------------|
| `monkeypatch` | Attribute/environment patching | For test isolation |
| `mocker` (pytest-mock) | Mock factory | Essential for test doubles |
| `capsys` / `capfd` | Capture stdout/stderr | No external I/O |
| `caplog` | Capture log output | No external I/O |
| `fs` (pyfakefs) | Fake filesystem | In-memory, no real I/O |

**Fixtures to Avoid in Small Tests:**

| Fixture | Why Avoid |
|---------|-----------|
| `tmp_path` | Filesystem access blocked in small tests |
| `tmp_path_factory` | Filesystem access blocked in small tests |
| Database fixtures | External I/O dependency |
| Network fixtures | Network access blocked |
| File fixtures with real paths | Filesystem access blocked |
| Session-scoped fixtures | Breaks test isolation |

---

### Medium Tests

Medium tests can use broader fixture scopes for shared resources:

| Fixture Scope | Recommendation |
|--------------|----------------|
| `function` | Good for test-specific state |
| `class` | Good for shared setup within test class |
| `module` | Acceptable for expensive local resources |
| `session` | Use for session-wide local services |

**Recommended Fixtures:**

```python
import pytest

@pytest.fixture(scope="module")
def test_database(tmp_path_factory):
    """Module-scoped test database."""
    db_path = tmp_path_factory.mktemp("db") / "test.db"
    db = Database(db_path)
    db.initialize()
    yield db
    db.close()

@pytest.fixture
def db_session(test_database):
    """Function-scoped database session."""
    session = test_database.create_session()
    yield session
    session.rollback()
    session.close()
```

**Allowed pytest Built-in Fixtures:**

All fixtures allowed for small tests, plus:

| Fixture | Description | Why Allowed |
|---------|-------------|-------------|
| `tmp_path` family | Temporary directories | File I/O allowed |
| `pytester` | For testing pytest plugins | Subprocess spawning allowed |

---

### Large Tests

Large tests have no fixture restrictions:

| Fixture Scope | Recommendation |
|--------------|----------------|
| `function` | For test-specific state |
| `class` | For class-shared resources |
| `module` | For expensive external resources |
| `session` | For session-wide services |

**Example Fixtures:**

```python
import pytest

@pytest.fixture(scope="session")
def api_server():
    """Session-wide external API connection."""
    server = ExternalAPIClient(
        base_url="https://api.example.com",
        api_key=os.environ["API_KEY"]
    )
    server.authenticate()
    yield server
    server.close()

@pytest.fixture(scope="module")
def test_environment(api_server):
    """Module-scoped test environment."""
    env = api_server.create_test_environment()
    yield env
    env.cleanup()
```

---

### XLarge Tests

XLarge tests follow the same patterns as large tests, with emphasis on efficient resource management for long-running tests:

```python
import pytest

@pytest.fixture(scope="session")
def load_test_framework():
    """Session-scoped load testing framework."""
    framework = LoadTestFramework()
    framework.initialize()
    yield framework
    framework.shutdown()
```

---

## Fixture Scope Best Practices

### Scope Selection Guide

```
Small Tests:  function > class > module
Medium Tests: function ~ class ~ module > session
Large Tests:  Depends on resource cost and reuse
```

### Anti-Patterns to Avoid

1. **Session fixtures in small tests:**
   ```python
   # BAD: Breaks test isolation
   @pytest.fixture(scope="session")
   def shared_state():
       return {"counter": 0}

   @pytest.mark.small
   def test_one(shared_state):
       shared_state["counter"] += 1  # Modifies shared state!
   ```

2. **Network fixtures in small tests:**
   ```python
   # BAD: Network is blocked in small tests
   @pytest.fixture
   def api_response():
       return requests.get("https://api.example.com/data")

   @pytest.mark.small
   def test_process_data(api_response):  # Will fail!
       pass
   ```

3. **Real database in small tests:**
   ```python
   # BAD: Database is blocked in small tests
   @pytest.fixture
   def db_session():
       engine = create_engine("sqlite:///test.db")
       Session = sessionmaker(bind=engine)
       return Session()

   @pytest.mark.small
   def test_query(db_session):  # Will fail!
       pass
   ```

---

## Fixture Patterns by Use Case

### Test Doubles for Small Tests

```python
import pytest

@pytest.fixture
def fake_repository():
    """In-memory repository for small tests."""
    class FakeRepository:
        def __init__(self):
            self._data = {}

        def save(self, id, entity):
            self._data[id] = entity

        def get(self, id):
            return self._data.get(id)

    return FakeRepository()

@pytest.mark.small
def test_service_saves_entity(fake_repository):
    service = EntityService(repository=fake_repository)
    service.create(id="123", name="Test")
    assert fake_repository.get("123")["name"] == "Test"
```

### Temporary Files for Medium Tests

```python
import pytest

@pytest.fixture
def config_file(tmp_path):
    """Create a temporary config file."""
    config = tmp_path / "config.yaml"
    config.write_text("debug: true\nlog_level: INFO")
    return config

@pytest.mark.medium
def test_load_configuration(config_file):
    config = load_config(config_file)
    assert config.debug is True
```

### Database Transactions for Medium Tests

```python
import pytest

@pytest.fixture
def db_transaction(test_database):
    """Database transaction that rolls back after each test."""
    connection = test_database.connect()
    transaction = connection.begin()
    yield connection
    transaction.rollback()
    connection.close()

@pytest.mark.medium
def test_insert_user(db_transaction):
    db_transaction.execute("INSERT INTO users (name) VALUES ('Test')")
    result = db_transaction.execute("SELECT name FROM users").fetchone()
    assert result[0] == "Test"
    # Transaction is rolled back automatically
```

---

## Compatibility with pytest Fixtures

pytest-test-categories is fully compatible with all standard pytest fixtures and popular fixture-providing plugins:

| Plugin | Compatibility | Notes |
|--------|--------------|-------|
| pytest-mock | Full | Recommended for small tests |
| pytest-asyncio | Full | Use appropriate markers |
| pytest-django | Full | Consider test size for DB tests |
| pytest-flask | Full | Consider test size for request tests |
| pytest-factoryboy | Full | Great for test data generation |
| pytest-lazy-fixture | Full | Works with size markers |
| pytest-xdist | Full | Parallel execution supported |

---

## Source Code References

While pytest-test-categories doesn't provide fixtures directly, these modules handle fixture-related interactions:

| Component | Location |
|-----------|----------|
| Filesystem blocker | [`adapters/filesystem.py`](https://github.com/mikelane/pytest-test-categories/blob/main/src/pytest_test_categories/adapters/filesystem.py) |
