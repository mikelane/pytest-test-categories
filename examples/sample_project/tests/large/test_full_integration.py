"""Full integration tests with real external dependencies.

These tests demonstrate large-sized tests that exercise the
complete system with real external services.

Note: Large tests should be used sparingly. Most testing should
be done with small and medium tests. Large tests are for
validating end-to-end flows that cannot be tested otherwise.

IMPORTANT: These tests may be slow, flaky, and require external
services to be available. They are typically run:
- Nightly in CI
- Before releases
- When debugging integration issues
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from sample_project.database import FakeProductRepository, Product
from sample_project.file_processor import FileProcessor

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def integration_temp_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary directory with sample data for integration tests.

    This fixture sets up a complete testing environment with
    sample files that can be used for end-to-end testing.
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    products_csv = data_dir / "products.csv"
    products_csv.write_text("name,price,quantity\nWidget,9.99,10\nGadget,19.99,5\n")

    users_json = data_dir / "users.json"
    users_json.write_text(
        json.dumps(
            [
                {"id": 1, "name": "Alice", "email": "alice@example.com"},
                {"id": 2, "name": "Bob", "email": "bob@example.com"},
            ]
        )
    )

    yield tmp_path


@pytest.mark.large
class DescribeCompleteDataPipeline:
    """Integration tests for complete data processing pipelines.

    These tests verify that multiple components work together
    correctly when processing real data through the system.
    """

    def it_processes_csv_through_complete_pipeline(
        self,
        integration_temp_dir: Path,
    ) -> None:
        """Test complete pipeline: CSV -> JSON -> Database -> Report."""
        processor = FileProcessor()
        repo = FakeProductRepository()

        csv_file = integration_temp_dir / "data" / "products.csv"
        json_file = integration_temp_dir / "products.json"

        csv_result = processor.csv_to_json(csv_file, json_file)
        assert csv_result.records_processed == 2
        assert len(csv_result.errors) == 0

        with json_file.open("r") as f:
            products_data = json.load(f)

        for product_data in products_data:
            product = Product(
                id=0,
                name=product_data["name"],
                price=float(product_data["price"]),
                quantity=int(product_data["quantity"]),
            )
            repo.save(product)

        all_products = repo.find_by_name("")
        assert len(all_products) == 2

        report = {
            "total_products": len(all_products),
            "total_value": sum(p.price * p.quantity for p in all_products),
        }

        assert report["total_products"] == 2
        assert report["total_value"] == pytest.approx(199.85, rel=1e-2)

    def it_handles_roundtrip_conversion(
        self,
        integration_temp_dir: Path,
    ) -> None:
        """Test that CSV -> JSON -> CSV preserves data."""
        processor = FileProcessor()

        original_csv = integration_temp_dir / "data" / "products.csv"
        original_csv.read_text()

        json_file = integration_temp_dir / "intermediate.json"
        final_csv = integration_temp_dir / "roundtrip.csv"

        processor.csv_to_json(original_csv, json_file)
        processor.json_to_csv(json_file, final_csv)

        final_content = final_csv.read_text()

        assert "name,price,quantity" in final_content
        assert "Widget" in final_content
        assert "Gadget" in final_content

    def it_merges_and_validates_multiple_sources(
        self,
        integration_temp_dir: Path,
    ) -> None:
        """Test merging data from multiple sources."""
        processor = FileProcessor()

        source1 = integration_temp_dir / "source1.json"
        source1.write_text('[{"id": 1, "type": "widget"}]')

        source2 = integration_temp_dir / "source2.json"
        source2.write_text('[{"id": 2, "type": "gadget"}]')

        source3 = integration_temp_dir / "source3.json"
        source3.write_text('[{"id": 3, "type": "tool"}]')

        merged = integration_temp_dir / "merged.json"

        result = processor.merge_json_files([source1, source2, source3], merged)

        assert result.records_processed == 3
        assert len(result.errors) == 0

        with merged.open("r") as f:
            data = json.load(f)

        assert len(data) == 3
        types = {item["type"] for item in data}
        assert types == {"widget", "gadget", "tool"}


@pytest.mark.large
class DescribeErrorRecoveryScenarios:
    """Integration tests for error handling and recovery.

    These tests verify that the system handles errors gracefully
    when processing invalid or corrupted data.
    """

    def it_continues_processing_after_partial_failure(
        self,
        integration_temp_dir: Path,
    ) -> None:
        """Test that processing continues when some files fail."""
        processor = FileProcessor()

        valid_file = integration_temp_dir / "valid.json"
        valid_file.write_text('[{"id": 1}]')

        invalid_file = integration_temp_dir / "invalid.json"
        invalid_file.write_text("not valid json{")

        valid_file2 = integration_temp_dir / "valid2.json"
        valid_file2.write_text('[{"id": 2}]')

        merged = integration_temp_dir / "merged.json"

        result = processor.merge_json_files(
            [valid_file, invalid_file, valid_file2],
            merged,
        )

        assert result.records_processed == 2
        assert len(result.errors) == 1
        assert "invalid.json" in result.errors[0]

    def it_handles_empty_input_gracefully(
        self,
        integration_temp_dir: Path,
    ) -> None:
        """Test handling of empty input files."""
        processor = FileProcessor()

        empty_json = integration_temp_dir / "empty.json"
        empty_json.write_text("[]")

        output_csv = integration_temp_dir / "output.csv"

        result = processor.json_to_csv(empty_json, output_csv)

        assert result.records_processed == 0
        assert len(result.errors) == 0
        assert output_csv.exists()
