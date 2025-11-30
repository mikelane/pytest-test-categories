"""Database access layer demonstrating repository pattern.

This module shows how to structure database access for testability:
- Small tests: Use in-memory fakes
- Medium tests: Use testcontainers for real database behavior
- Large tests: Test against actual database instances
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass
class Product:
    """Product entity stored in the database."""

    id: int
    name: str
    price: float
    quantity: int


class ProductRepository(ABC):
    """Abstract repository for product persistence.

    This follows the Repository pattern, allowing easy substitution
    of implementations for different test sizes:

    - Small tests: Use FakeProductRepository (in-memory)
    - Medium tests: Use PostgresProductRepository with testcontainers
    - Large tests: Use PostgresProductRepository with real database
    """

    @abstractmethod
    def get_by_id(self, product_id: int) -> Product | None:
        """Fetch a product by ID."""
        ...

    @abstractmethod
    def save(self, product: Product) -> Product:
        """Save a product, returning the saved entity."""
        ...

    @abstractmethod
    def delete(self, product_id: int) -> bool:
        """Delete a product by ID, returning True if deleted."""
        ...

    @abstractmethod
    def find_by_name(self, name: str) -> list[Product]:
        """Find products matching a name pattern."""
        ...


@dataclass
class FakeProductRepository(ProductRepository):
    """In-memory fake repository for small tests.

    This fake provides the same interface as the real repository
    but stores data in memory. Perfect for fast, hermetic tests.
    """

    _products: dict[int, Product] = field(default_factory=dict)
    _next_id: int = 1

    def get_by_id(self, product_id: int) -> Product | None:
        """Fetch a product by ID from memory."""
        return self._products.get(product_id)

    def save(self, product: Product) -> Product:
        """Save a product to memory."""
        if product.id == 0:
            product = Product(
                id=self._next_id,
                name=product.name,
                price=product.price,
                quantity=product.quantity,
            )
            self._next_id += 1
        self._products[product.id] = product
        return product

    def delete(self, product_id: int) -> bool:
        """Delete a product from memory."""
        if product_id in self._products:
            del self._products[product_id]
            return True
        return False

    def find_by_name(self, name: str) -> list[Product]:
        """Find products matching a name pattern (case-insensitive)."""
        name_lower = name.lower()
        return [p for p in self._products.values() if name_lower in p.name.lower()]


class PostgresProductRepository(ProductRepository):
    """PostgreSQL repository implementation.

    Used in medium tests (with testcontainers) and large tests
    (with real database connections).
    """

    def __init__(self, connection_params: Mapping[str, str | int]) -> None:
        """Initialize with database connection parameters.

        Args:
            connection_params: Dict with host, port, database, user, password.

        """
        self._params = connection_params
        self._conn = None

    def _get_connection(self):  # noqa: ANN202
        """Get or create database connection."""
        if self._conn is None:
            import psycopg2

            self._conn = psycopg2.connect(
                host=str(self._params["host"]),
                port=int(self._params["port"]),
                database=str(self._params["database"]),
                user=str(self._params["user"]),
                password=str(self._params["password"]),
            )
        return self._conn

    def get_by_id(self, product_id: int) -> Product | None:
        """Fetch a product by ID from PostgreSQL."""
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, price, quantity FROM products WHERE id = %s",
                (product_id,),
            )
            row = cur.fetchone()
            if row:
                return Product(id=row[0], name=row[1], price=row[2], quantity=row[3])
        return None

    def save(self, product: Product) -> Product:
        """Save a product to PostgreSQL."""
        conn = self._get_connection()
        with conn.cursor() as cur:
            if product.id == 0:
                cur.execute(
                    "INSERT INTO products (name, price, quantity) VALUES (%s, %s, %s) RETURNING id",
                    (product.name, product.price, product.quantity),
                )
                new_id = cur.fetchone()[0]
                product = Product(
                    id=new_id,
                    name=product.name,
                    price=product.price,
                    quantity=product.quantity,
                )
            else:
                cur.execute(
                    "UPDATE products SET name = %s, price = %s, quantity = %s WHERE id = %s",
                    (product.name, product.price, product.quantity, product.id),
                )
            conn.commit()
        return product

    def delete(self, product_id: int) -> bool:
        """Delete a product from PostgreSQL."""
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
            deleted = cur.rowcount > 0
            conn.commit()
        return deleted

    def find_by_name(self, name: str) -> list[Product]:
        """Find products matching a name pattern."""
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, price, quantity FROM products WHERE LOWER(name) LIKE LOWER(%s)",
                (f"%{name}%",),
            )
            return [
                Product(id=row[0], name=row[1], price=row[2], quantity=row[3])
                for row in cur.fetchall()
            ]

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
