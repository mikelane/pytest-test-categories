"""Pytest configuration and shared fixtures for sample_project tests.

This conftest.py demonstrates:
1. Shared fixtures available across all test modules
2. Configuration for pytest-test-categories
3. Fixture organization by test size
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from sample_project.database import FakeProductRepository, Product

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def sample_products() -> list[Product]:
    """Provide a set of sample products for testing.

    This fixture is usable by all test sizes since it creates
    pure Python objects with no external dependencies.
    """
    return [
        Product(id=1, name="Widget", price=9.99, quantity=10),
        Product(id=2, name="Gadget", price=19.99, quantity=5),
        Product(id=3, name="Tool", price=29.99, quantity=3),
    ]


@pytest.fixture
def product_repository(sample_products: list[Product]) -> FakeProductRepository:
    """Provide a pre-populated fake repository.

    This fixture is appropriate for small tests since it uses
    an in-memory fake rather than a real database.
    """
    repo = FakeProductRepository()
    for product in sample_products:
        repo.save(product)
    return repo


@pytest.fixture
def sample_csv_content() -> str:
    """Provide sample CSV content for file processing tests."""
    return "name,price,quantity\nWidget,9.99,10\nGadget,19.99,5\n"


@pytest.fixture
def sample_json_content() -> str:
    """Provide sample JSON content for file processing tests."""
    return json.dumps(
        [
            {"name": "Widget", "price": "9.99", "quantity": "10"},
            {"name": "Gadget", "price": "19.99", "quantity": "5"},
        ]
    )


@pytest.fixture
def data_files(
    tmp_path: Path,
    sample_csv_content: str,
    sample_json_content: str,
) -> Generator[dict[str, Path], None, None]:
    """Create sample data files for testing.

    This fixture uses tmp_path to create isolated test files,
    making it safe for small tests.

    Yields:
        Dictionary mapping file type to Path.

    """
    csv_file = tmp_path / "data.csv"
    csv_file.write_text(sample_csv_content)

    json_file = tmp_path / "data.json"
    json_file.write_text(sample_json_content)

    yield {
        "csv": csv_file,
        "json": json_file,
        "output_dir": tmp_path,
    }
