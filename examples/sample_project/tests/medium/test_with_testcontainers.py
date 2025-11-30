"""Tests using testcontainers for database integration.

These tests demonstrate medium-sized tests that use testcontainers
to run real database instances in Docker containers.

IMPORTANT: Use @pytest.mark.medium(allow_external_systems=True) to
indicate that this test intentionally uses external systems (Docker).
This suppresses the pytest-test-categories warning about testcontainers.

Note: These tests require Docker to be installed and running.
They are skipped if Docker is not available.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from sample_project.database import PostgresProductRepository, Product

if TYPE_CHECKING:
    from collections.abc import Generator

# Check if testcontainers is available
try:
    from testcontainers.postgres import PostgresContainer

    HAS_TESTCONTAINERS = True
except ImportError:
    HAS_TESTCONTAINERS = False
    PostgresContainer = None  # type: ignore[assignment, misc]


@pytest.fixture
def postgres_container() -> Generator[PostgresContainer, None, None]:
    """Start a PostgreSQL container for testing.

    This fixture uses testcontainers to spin up a real PostgreSQL
    instance in Docker. The container is automatically cleaned up
    after the test completes.

    Yields:
        The PostgresContainer instance with connection info.

    """
    with PostgresContainer("postgres:15-alpine") as postgres:
        # Create the products table
        import psycopg2

        conn = psycopg2.connect(
            host=postgres.get_container_host_ip(),
            port=postgres.get_exposed_port(5432),
            database=postgres.dbname,
            user=postgres.username,
            password=postgres.password,
        )
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE products (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    price DECIMAL(10, 2) NOT NULL,
                    quantity INTEGER NOT NULL
                )
            """)
            conn.commit()
        conn.close()

        yield postgres


@pytest.mark.skipif(not HAS_TESTCONTAINERS, reason="testcontainers not installed")
@pytest.mark.medium(allow_external_systems=True)
class DescribePostgresProductRepositoryWithContainer:
    """Tests for PostgresProductRepository using testcontainers.

    These tests verify real database behavior using PostgreSQL
    running in a Docker container. This catches issues that
    in-memory fakes might miss (SQL syntax, constraints, etc.).

    The allow_external_systems=True marker tells pytest-test-categories
    that we intentionally use Docker/testcontainers in this test.
    """

    def it_saves_and_retrieves_product(self, postgres_container) -> None:
        repo = PostgresProductRepository(
            connection_params={
                "host": postgres_container.get_container_host_ip(),
                "port": postgres_container.get_exposed_port(5432),
                "database": postgres_container.dbname,
                "user": postgres_container.username,
                "password": postgres_container.password,
            }
        )
        product = Product(id=0, name="Widget", price=9.99, quantity=10)

        saved = repo.save(product)
        retrieved = repo.get_by_id(saved.id)

        assert retrieved is not None
        assert retrieved.name == "Widget"
        assert float(retrieved.price) == 9.99
        repo.close()

    def it_updates_existing_product(self, postgres_container) -> None:
        repo = PostgresProductRepository(
            connection_params={
                "host": postgres_container.get_container_host_ip(),
                "port": postgres_container.get_exposed_port(5432),
                "database": postgres_container.dbname,
                "user": postgres_container.username,
                "password": postgres_container.password,
            }
        )
        product = repo.save(Product(id=0, name="Gadget", price=19.99, quantity=5))

        product = Product(id=product.id, name="Updated Gadget", price=24.99, quantity=3)
        repo.save(product)
        retrieved = repo.get_by_id(product.id)

        assert retrieved is not None
        assert retrieved.name == "Updated Gadget"
        assert float(retrieved.price) == 24.99
        repo.close()

    def it_deletes_product(self, postgres_container) -> None:
        repo = PostgresProductRepository(
            connection_params={
                "host": postgres_container.get_container_host_ip(),
                "port": postgres_container.get_exposed_port(5432),
                "database": postgres_container.dbname,
                "user": postgres_container.username,
                "password": postgres_container.password,
            }
        )
        product = repo.save(Product(id=0, name="ToDelete", price=1.00, quantity=1))

        deleted = repo.delete(product.id)
        retrieved = repo.get_by_id(product.id)

        assert deleted is True
        assert retrieved is None
        repo.close()

    def it_finds_products_by_name(self, postgres_container) -> None:
        repo = PostgresProductRepository(
            connection_params={
                "host": postgres_container.get_container_host_ip(),
                "port": postgres_container.get_exposed_port(5432),
                "database": postgres_container.dbname,
                "user": postgres_container.username,
                "password": postgres_container.password,
            }
        )
        repo.save(Product(id=0, name="Blue Widget", price=9.99, quantity=10))
        repo.save(Product(id=0, name="Red Widget", price=12.99, quantity=5))
        repo.save(Product(id=0, name="Gadget", price=19.99, quantity=3))

        widgets = repo.find_by_name("Widget")

        assert len(widgets) == 2
        repo.close()
