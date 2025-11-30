"""Pure logic tests that require no mocking.

These are the ideal small tests: fast, deterministic, and self-contained.
They test pure functions and data transformations with no external dependencies.
"""

from __future__ import annotations

import pytest

from sample_project.api_client import ApiError, User
from sample_project.database import Product
from sample_project.file_processor import ProcessingResult


@pytest.mark.small
class DescribeUser:
    """Tests for the User dataclass."""

    def it_creates_user_with_all_fields(self) -> None:
        user = User(id=1, name="Alice", email="alice@example.com")

        assert user.id == 1
        assert user.name == "Alice"
        assert user.email == "alice@example.com"

    def it_supports_equality_comparison(self) -> None:
        user1 = User(id=1, name="Alice", email="alice@example.com")
        user2 = User(id=1, name="Alice", email="alice@example.com")

        assert user1 == user2


@pytest.mark.small
class DescribeApiError:
    """Tests for the ApiError exception."""

    def it_stores_status_code_and_message(self) -> None:
        error = ApiError(status_code=404, message="User not found")

        assert error.status_code == 404
        assert error.message == "User not found"

    def it_is_an_exception_subclass(self) -> None:
        error = ApiError(status_code=500, message="Server error")

        with pytest.raises(ApiError):
            raise error


@pytest.mark.small
class DescribeProduct:
    """Tests for the Product dataclass."""

    def it_creates_product_with_all_fields(self) -> None:
        product = Product(id=1, name="Widget", price=9.99, quantity=100)

        assert product.id == 1
        assert product.name == "Widget"
        assert product.price == 9.99
        assert product.quantity == 100

    @pytest.mark.parametrize(
        ("price", "quantity", "expected_total"),
        [
            (10.00, 5, 50.00),
            (0.99, 100, 99.00),
            (1000.00, 1, 1000.00),
        ],
    )
    def it_calculates_inventory_value(
        self,
        price: float,
        quantity: int,
        expected_total: float,
    ) -> None:
        product = Product(id=1, name="Item", price=price, quantity=quantity)

        total_value = product.price * product.quantity

        assert total_value == expected_total


@pytest.mark.small
class DescribeProcessingResult:
    """Tests for the ProcessingResult dataclass."""

    def it_tracks_records_processed(self, tmp_path) -> None:
        result = ProcessingResult(
            input_file=tmp_path / "input.csv",
            output_file=tmp_path / "output.json",
            records_processed=42,
            errors=[],
        )

        assert result.records_processed == 42
        assert len(result.errors) == 0

    def it_tracks_processing_errors(self, tmp_path) -> None:
        errors = ["Row 5: Invalid data", "Row 10: Missing field"]
        result = ProcessingResult(
            input_file=tmp_path / "input.csv",
            output_file=tmp_path / "output.json",
            records_processed=8,
            errors=errors,
        )

        assert len(result.errors) == 2
        assert "Row 5" in result.errors[0]
