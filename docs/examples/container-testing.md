# Container Testing with Testcontainers

This guide demonstrates how to use [testcontainers-python](https://testcontainers-python.readthedocs.io/) with pytest-test-categories for integration testing against real databases and services.

## Why Use Testcontainers?

Testcontainers provides ephemeral Docker containers for integration testing:

- **Real services**: Test against actual PostgreSQL, Redis, Kafka, etc.
- **Isolation**: Each test run gets fresh containers
- **Reproducibility**: Same container images across all environments
- **No shared state**: Containers are destroyed after tests

## Test Size Considerations

Container tests are **medium tests** because they:

- Access localhost (Docker daemon)
- Start external processes (containers)
- May take several seconds to initialize
- Use real network connections

```python
@pytest.mark.medium
def test_with_postgres_container(postgres_container):
    """Medium test: accesses localhost via Docker."""
    ...
```

## Installation

```bash
pip install testcontainers
# or for specific modules
pip install testcontainers[postgres]
pip install testcontainers[redis]
pip install testcontainers[kafka]

# With uv
uv add --dev "testcontainers[postgres,redis]"
```

## PostgreSQL Container

### Basic Usage

```python
import pytest
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="module")
def postgres_container():
    """Start PostgreSQL container for the test module."""
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres


@pytest.mark.medium
def test_creates_user_in_database(postgres_container):
    """Test user creation with real PostgreSQL."""
    import psycopg2

    conn = psycopg2.connect(postgres_container.get_connection_url())
    cursor = conn.cursor()

    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL
        )
    """)

    # Insert user
    cursor.execute(
        "INSERT INTO users (name, email) VALUES (%s, %s) RETURNING id",
        ("Alice", "alice@example.com"),
    )
    user_id = cursor.fetchone()[0]
    conn.commit()

    # Verify
    cursor.execute("SELECT name FROM users WHERE id = %s", (user_id,))
    name = cursor.fetchone()[0]

    assert name == "Alice"

    cursor.close()
    conn.close()
```

### With SQLAlchemy

```python
import pytest
from sqlalchemy import create_engine, text
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="module")
def postgres_engine(postgres_container):
    """Create SQLAlchemy engine connected to container."""
    engine = create_engine(postgres_container.get_connection_url())
    yield engine
    engine.dispose()


@pytest.mark.medium
def test_sqlalchemy_operations(postgres_engine):
    """Test SQLAlchemy with real PostgreSQL."""
    with postgres_engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                price DECIMAL(10, 2)
            )
        """))
        conn.execute(
            text("INSERT INTO products (name, price) VALUES (:name, :price)"),
            {"name": "Widget", "price": 19.99},
        )
        conn.commit()

        result = conn.execute(text("SELECT price FROM products WHERE name = :name"), {"name": "Widget"})
        price = result.scalar()

    assert float(price) == 19.99
```

### Pre-initialized Database

```python
@pytest.fixture(scope="module")
def postgres_with_schema():
    """Start PostgreSQL with pre-initialized schema."""
    with PostgresContainer("postgres:16-alpine") as postgres:
        import psycopg2

        conn = psycopg2.connect(postgres.get_connection_url())
        cursor = conn.cursor()

        # Initialize schema
        cursor.execute("""
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                total DECIMAL(10, 2),
                status VARCHAR(50) DEFAULT 'pending'
            );

            CREATE INDEX idx_orders_user ON orders(user_id);
        """)
        conn.commit()
        cursor.close()
        conn.close()

        yield postgres


@pytest.mark.medium
def test_order_creation(postgres_with_schema):
    """Test order creation with pre-initialized schema."""
    import psycopg2

    conn = psycopg2.connect(postgres_with_schema.get_connection_url())
    cursor = conn.cursor()

    # Create user
    cursor.execute(
        "INSERT INTO users (name, email) VALUES (%s, %s) RETURNING id",
        ("Bob", "bob@example.com"),
    )
    user_id = cursor.fetchone()[0]

    # Create order
    cursor.execute(
        "INSERT INTO orders (user_id, total) VALUES (%s, %s) RETURNING id",
        (user_id, 99.99),
    )
    order_id = cursor.fetchone()[0]
    conn.commit()

    # Verify
    cursor.execute("SELECT status FROM orders WHERE id = %s", (order_id,))
    status = cursor.fetchone()[0]

    assert status == "pending"

    cursor.close()
    conn.close()
```

## Redis Container

```python
import pytest
from testcontainers.redis import RedisContainer


@pytest.fixture(scope="module")
def redis_container():
    """Start Redis container."""
    with RedisContainer("redis:7-alpine") as redis:
        yield redis


@pytest.fixture
def redis_client(redis_container):
    """Get Redis client connected to container."""
    import redis

    client = redis.Redis(
        host=redis_container.get_container_host_ip(),
        port=redis_container.get_exposed_port(6379),
        decode_responses=True,
    )
    yield client
    client.flushall()  # Clean up after each test


@pytest.mark.medium
def test_caches_user_session(redis_client):
    """Test session caching with real Redis."""
    session_data = {"user_id": "123", "role": "admin"}

    redis_client.hset("session:abc123", mapping=session_data)
    redis_client.expire("session:abc123", 3600)

    cached = redis_client.hgetall("session:abc123")

    assert cached["user_id"] == "123"
    assert cached["role"] == "admin"


@pytest.mark.medium
def test_rate_limiting(redis_client):
    """Test rate limiting logic with real Redis."""
    key = "rate:user:123"

    # Simulate 5 requests
    for _ in range(5):
        redis_client.incr(key)

    count = int(redis_client.get(key))

    assert count == 5
```

## MySQL Container

```python
import pytest
from testcontainers.mysql import MySqlContainer


@pytest.fixture(scope="module")
def mysql_container():
    """Start MySQL container."""
    with MySqlContainer("mysql:8.0") as mysql:
        yield mysql


@pytest.mark.medium
def test_mysql_operations(mysql_container):
    """Test with real MySQL database."""
    import mysql.connector

    conn = mysql.connector.connect(
        host=mysql_container.get_container_host_ip(),
        port=mysql_container.get_exposed_port(3306),
        user=mysql_container.username,
        password=mysql_container.password,
        database=mysql_container.dbname,
    )
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255)
        )
    """)
    cursor.execute("INSERT INTO items (name) VALUES (%s)", ("Test Item",))
    conn.commit()

    cursor.execute("SELECT name FROM items WHERE id = LAST_INSERT_ID()")
    name = cursor.fetchone()[0]

    assert name == "Test Item"

    cursor.close()
    conn.close()
```

## MongoDB Container

```python
import pytest
from testcontainers.mongodb import MongoDbContainer


@pytest.fixture(scope="module")
def mongo_container():
    """Start MongoDB container."""
    with MongoDbContainer("mongo:7.0") as mongo:
        yield mongo


@pytest.mark.medium
def test_document_operations(mongo_container):
    """Test with real MongoDB."""
    from pymongo import MongoClient

    client = MongoClient(mongo_container.get_connection_url())
    db = client.test_database
    collection = db.users

    # Insert document
    result = collection.insert_one({
        "name": "Alice",
        "email": "alice@example.com",
        "tags": ["developer", "python"],
    })

    # Query
    user = collection.find_one({"_id": result.inserted_id})

    assert user["name"] == "Alice"
    assert "python" in user["tags"]

    client.close()
```

## Kafka Container

```python
import pytest
from testcontainers.kafka import KafkaContainer


@pytest.fixture(scope="module")
def kafka_container():
    """Start Kafka container."""
    with KafkaContainer("confluentinc/cp-kafka:7.5.0") as kafka:
        yield kafka


@pytest.mark.medium
def test_produces_and_consumes_message(kafka_container):
    """Test Kafka message flow."""
    from kafka import KafkaProducer, KafkaConsumer

    bootstrap_servers = kafka_container.get_bootstrap_server()

    # Produce message
    producer = KafkaProducer(bootstrap_servers=bootstrap_servers)
    producer.send("test-topic", b"Hello Kafka")
    producer.flush()
    producer.close()

    # Consume message
    consumer = KafkaConsumer(
        "test-topic",
        bootstrap_servers=bootstrap_servers,
        auto_offset_reset="earliest",
        consumer_timeout_ms=5000,
    )

    messages = list(consumer)
    consumer.close()

    assert len(messages) == 1
    assert messages[0].value == b"Hello Kafka"
```

## Elasticsearch Container

```python
import pytest
from testcontainers.elasticsearch import ElasticSearchContainer


@pytest.fixture(scope="module")
def elasticsearch_container():
    """Start Elasticsearch container."""
    with ElasticSearchContainer("elasticsearch:8.11.0") as es:
        yield es


@pytest.mark.medium
def test_indexes_and_searches_document(elasticsearch_container):
    """Test Elasticsearch indexing and search."""
    from elasticsearch import Elasticsearch

    es = Elasticsearch(elasticsearch_container.get_url())

    # Index document
    es.index(
        index="products",
        id="1",
        document={
            "name": "Python Book",
            "description": "Learn Python programming",
            "price": 29.99,
        },
        refresh=True,  # Make immediately searchable
    )

    # Search
    result = es.search(
        index="products",
        query={"match": {"description": "Python"}},
    )

    assert result["hits"]["total"]["value"] == 1
    assert result["hits"]["hits"][0]["_source"]["name"] == "Python Book"
```

## Fixture Scoping Strategies

### Module Scope (Recommended for Speed)

```python
@pytest.fixture(scope="module")
def postgres_container():
    """One container for all tests in module."""
    with PostgresContainer() as postgres:
        yield postgres
```

Advantages:
- Container starts once per module
- Tests run faster
- Lower Docker overhead

Disadvantages:
- Tests may share state
- Need cleanup between tests

### Function Scope (Maximum Isolation)

```python
@pytest.fixture(scope="function")
def postgres_container():
    """Fresh container for each test."""
    with PostgresContainer() as postgres:
        yield postgres
```

Advantages:
- Complete isolation
- No shared state

Disadvantages:
- Slower (container starts for each test)
- Higher resource usage

### Session Scope (Maximum Speed)

```python
@pytest.fixture(scope="session")
def postgres_container():
    """One container for entire test session."""
    with PostgresContainer() as postgres:
        yield postgres
```

Advantages:
- Fastest execution
- Minimal Docker overhead

Disadvantages:
- State persists across all tests
- Requires careful cleanup

### Hybrid Approach

```python
@pytest.fixture(scope="module")
def postgres_container():
    """Container per module."""
    with PostgresContainer() as postgres:
        yield postgres


@pytest.fixture
def db_connection(postgres_container):
    """Fresh connection per test with transaction rollback."""
    import psycopg2

    conn = psycopg2.connect(postgres_container.get_connection_url())
    conn.autocommit = False
    yield conn
    conn.rollback()  # Undo any changes
    conn.close()
```

## When to Use Large vs Medium

### Medium Tests (Default for Containers)

Use `@pytest.mark.medium` when:
- Accessing containers on localhost
- Tests complete within 5 minutes
- No external network access needed

```python
@pytest.mark.medium
def test_database_migration(postgres_container):
    """Migration test with local PostgreSQL container."""
    ...
```

### Large Tests (External Access)

Use `@pytest.mark.large` when:
- Container connects to external services
- Tests access external networks
- Extended test duration needed

```python
@pytest.mark.large
def test_replication_to_external_service(postgres_container):
    """Test that replicates data to external staging database."""
    ...
```

## Skipping When Docker Unavailable

```python
import pytest

try:
    import docker
    docker.from_env().ping()
    DOCKER_AVAILABLE = True
except Exception:
    DOCKER_AVAILABLE = False


@pytest.mark.skipif(not DOCKER_AVAILABLE, reason="Docker not available")
@pytest.mark.medium
def test_with_container(postgres_container):
    """Test that requires Docker."""
    ...
```

Or use a fixture:

```python
@pytest.fixture(scope="session")
def docker_available():
    """Check if Docker is available."""
    try:
        import docker
        docker.from_env().ping()
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def postgres_container(docker_available):
    """PostgreSQL container, skips if Docker unavailable."""
    if not docker_available:
        pytest.skip("Docker not available")

    from testcontainers.postgres import PostgresContainer

    with PostgresContainer() as postgres:
        yield postgres
```

## Best Practices

### 1. Use Alpine Images When Possible

```python
# Faster to pull and start
PostgresContainer("postgres:16-alpine")
RedisContainer("redis:7-alpine")
```

### 2. Pre-pull Images in CI

```yaml
# .github/workflows/test.yml
- name: Pull container images
  run: |
    docker pull postgres:16-alpine
    docker pull redis:7-alpine
```

### 3. Clean Up Between Tests

```python
@pytest.fixture
def clean_database(postgres_container):
    """Provide clean database for each test."""
    import psycopg2

    conn = psycopg2.connect(postgres_container.get_connection_url())
    cursor = conn.cursor()

    yield conn

    # Clean up tables after test
    cursor.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    conn.commit()
    cursor.close()
    conn.close()
```

### 4. Use Environment Variables for Configuration

```python
@pytest.fixture(scope="module")
def postgres_container():
    """Configure container via environment."""
    with PostgresContainer(
        "postgres:16-alpine",
        username=os.getenv("TEST_DB_USER", "test"),
        password=os.getenv("TEST_DB_PASS", "test"),
        dbname=os.getenv("TEST_DB_NAME", "testdb"),
    ) as postgres:
        yield postgres
```

## Related Documentation

- [Database Testing](database-testing.md) - Patterns for database testing
- [Common Patterns](common-patterns.md) - General testing patterns
- [CI Integration](ci-integration.md) - Running container tests in CI
