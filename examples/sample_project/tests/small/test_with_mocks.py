"""Tests using mocks for external dependencies.

These tests demonstrate how to use mocks to isolate code under test
from external systems like HTTP APIs and databases.

Key patterns shown:
1. HTTP mocking with pytest-httpx
2. Database fakes using the repository pattern
3. Dependency injection for testability
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from sample_project.api_client import ApiClient, ApiError
from sample_project.database import FakeProductRepository, Product

if TYPE_CHECKING:
    from pytest_httpx import HTTPXMock


@pytest.mark.small
class DescribeApiClientWithMocks:
    """Tests for ApiClient using HTTP mocking.

    These tests use pytest-httpx to intercept HTTP requests,
    making them fast and hermetic (no network access).
    """

    def it_fetches_user_from_api(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://api.example.com/users/1",
            json={"id": 1, "name": "Alice", "email": "alice@example.com"},
        )
        client = ApiClient(base_url="https://api.example.com")

        user = client.get_user(1)

        assert user.id == 1
        assert user.name == "Alice"
        assert user.email == "alice@example.com"

    def it_raises_error_on_404_response(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://api.example.com/users/999",
            status_code=404,
        )
        client = ApiClient(base_url="https://api.example.com")

        with pytest.raises(ApiError) as exc_info:
            client.get_user(999)

        assert exc_info.value.status_code == 404

    def it_creates_user_via_api(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://api.example.com/users",
            method="POST",
            json={"id": 42, "name": "Bob", "email": "bob@example.com"},
            status_code=201,
        )
        client = ApiClient(base_url="https://api.example.com")

        user = client.create_user(name="Bob", email="bob@example.com")

        assert user.id == 42
        assert user.name == "Bob"

    def it_handles_server_error_on_create(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://api.example.com/users",
            method="POST",
            status_code=500,
        )
        client = ApiClient(base_url="https://api.example.com")

        with pytest.raises(ApiError) as exc_info:
            client.create_user(name="Test", email="test@example.com")

        assert exc_info.value.status_code == 500


@pytest.mark.small
class DescribeFakeProductRepository:
    """Tests for the in-memory fake repository.

    The fake repository allows testing business logic that depends
    on data persistence without actually hitting a database.
    """

    def it_saves_and_retrieves_product(self) -> None:
        repo = FakeProductRepository()
        product = Product(id=0, name="Widget", price=9.99, quantity=10)

        saved = repo.save(product)
        retrieved = repo.get_by_id(saved.id)

        assert retrieved is not None
        assert retrieved.name == "Widget"
        assert retrieved.id > 0

    def it_returns_none_for_missing_product(self) -> None:
        repo = FakeProductRepository()

        result = repo.get_by_id(999)

        assert result is None

    def it_deletes_product(self) -> None:
        repo = FakeProductRepository()
        product = repo.save(Product(id=0, name="ToDelete", price=1.00, quantity=1))

        deleted = repo.delete(product.id)
        retrieved = repo.get_by_id(product.id)

        assert deleted is True
        assert retrieved is None

    def it_returns_false_when_deleting_nonexistent(self) -> None:
        repo = FakeProductRepository()

        deleted = repo.delete(999)

        assert deleted is False

    def it_finds_products_by_name(self) -> None:
        repo = FakeProductRepository()
        repo.save(Product(id=0, name="Blue Widget", price=9.99, quantity=10))
        repo.save(Product(id=0, name="Red Widget", price=12.99, quantity=5))
        repo.save(Product(id=0, name="Gadget", price=19.99, quantity=3))

        widgets = repo.find_by_name("widget")

        assert len(widgets) == 2
        assert all("Widget" in p.name for p in widgets)


@pytest.mark.small
class DescribeFileProcessorWithTmpPath:
    """Tests for FileProcessor using pytest's tmp_path fixture.

    The tmp_path fixture provides an isolated temporary directory
    that is automatically cleaned up. This allows testing file
    operations without touching the real filesystem.
    """

    def it_converts_csv_to_json(self, tmp_path: Path) -> None:
        from sample_project.file_processor import FileProcessor

        csv_file = tmp_path / "data.csv"
        csv_file.write_text("name,age\nAlice,30\nBob,25\n")
        json_file = tmp_path / "data.json"

        processor = FileProcessor()
        result = processor.csv_to_json(csv_file, json_file)

        assert result.records_processed == 2
        assert json_file.exists()
        assert "Alice" in json_file.read_text()

    def it_converts_json_to_csv(self, tmp_path: Path) -> None:
        from sample_project.file_processor import FileProcessor

        json_file = tmp_path / "data.json"
        json_file.write_text('[{"name": "Alice", "age": "30"}]')
        csv_file = tmp_path / "data.csv"

        processor = FileProcessor()
        result = processor.json_to_csv(json_file, csv_file)

        assert result.records_processed == 1
        assert "name,age" in csv_file.read_text()

    def it_handles_empty_json_array(self, tmp_path: Path) -> None:
        from sample_project.file_processor import FileProcessor

        json_file = tmp_path / "empty.json"
        json_file.write_text("[]")
        csv_file = tmp_path / "empty.csv"

        processor = FileProcessor()
        result = processor.json_to_csv(json_file, csv_file)

        assert result.records_processed == 0

    def it_merges_multiple_json_files(self, tmp_path: Path) -> None:
        from sample_project.file_processor import FileProcessor

        file1 = tmp_path / "file1.json"
        file1.write_text('[{"id": 1}, {"id": 2}]')
        file2 = tmp_path / "file2.json"
        file2.write_text('[{"id": 3}]')
        output = tmp_path / "merged.json"

        processor = FileProcessor()
        result = processor.merge_json_files([file1, file2], output)

        assert result.records_processed == 3


@pytest.mark.small
class DescribeFileValidation:
    """Tests for file validation utilities."""

    def it_validates_correct_json(self, tmp_path: Path) -> None:
        from sample_project.file_processor import validate_json_file

        json_file = tmp_path / "valid.json"
        json_file.write_text('{"key": "value"}')

        is_valid, error = validate_json_file(json_file)

        assert is_valid is True
        assert error == ""

    def it_detects_invalid_json(self, tmp_path: Path) -> None:
        from sample_project.file_processor import validate_json_file

        json_file = tmp_path / "invalid.json"
        json_file.write_text("{key: value}")  # Missing quotes

        is_valid, error = validate_json_file(json_file)

        assert is_valid is False
        assert "Expecting property name" in error

    def it_counts_lines_in_file(self, tmp_path: Path) -> None:
        from sample_project.file_processor import count_lines

        text_file = tmp_path / "lines.txt"
        text_file.write_text("line 1\nline 2\nline 3\n")

        count = count_lines(text_file)

        assert count == 3
