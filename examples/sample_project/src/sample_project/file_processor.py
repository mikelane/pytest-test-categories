"""File processing utilities demonstrating filesystem operations.

This module shows patterns for file operations that can be tested:
- Small tests: Use tmp_path fixture for isolated file operations
- Large tests: Test against real file systems with cleanup
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProcessingResult:
    """Result of a file processing operation."""

    input_file: Path
    output_file: Path
    records_processed: int
    errors: list[str]


class FileProcessor:
    """Processes data files with various transformations.

    All file operations are designed to work with Path objects,
    making them easy to test with tmp_path fixtures.
    """

    def csv_to_json(self, input_path: Path, output_path: Path) -> ProcessingResult:
        """Convert a CSV file to JSON format.

        Args:
            input_path: Path to the input CSV file.
            output_path: Path where JSON output will be written.

        Returns:
            ProcessingResult with details about the operation.

        """
        errors: list[str] = []
        records: list[dict[str, str]] = []

        with input_path.open("r", newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row_num, row in enumerate(reader, start=1):
                try:
                    records.append(dict(row))
                except Exception as e:  # noqa: BLE001
                    errors.append(f"Row {row_num}: {e}")

        with output_path.open("w", encoding="utf-8") as jsonfile:
            json.dump(records, jsonfile, indent=2)

        return ProcessingResult(
            input_file=input_path,
            output_file=output_path,
            records_processed=len(records),
            errors=errors,
        )

    def json_to_csv(self, input_path: Path, output_path: Path) -> ProcessingResult:
        """Convert a JSON file to CSV format.

        Args:
            input_path: Path to the input JSON file (must be array of objects).
            output_path: Path where CSV output will be written.

        Returns:
            ProcessingResult with details about the operation.

        """
        errors: list[str] = []

        with input_path.open("r", encoding="utf-8") as jsonfile:
            data = json.load(jsonfile)

        if not isinstance(data, list):
            msg = "JSON file must contain an array of objects"
            raise ValueError(msg)

        if not data:
            output_path.write_text("")
            return ProcessingResult(
                input_file=input_path,
                output_file=output_path,
                records_processed=0,
                errors=errors,
            )

        fieldnames = list(data[0].keys())

        with output_path.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row_num, record in enumerate(data, start=1):
                try:
                    writer.writerow(record)
                except Exception as e:  # noqa: BLE001
                    errors.append(f"Record {row_num}: {e}")

        return ProcessingResult(
            input_file=input_path,
            output_file=output_path,
            records_processed=len(data),
            errors=errors,
        )

    def merge_json_files(
        self, input_paths: list[Path], output_path: Path
    ) -> ProcessingResult:
        """Merge multiple JSON array files into one.

        Args:
            input_paths: List of paths to JSON files to merge.
            output_path: Path where merged output will be written.

        Returns:
            ProcessingResult with details about the operation.

        """
        errors: list[str] = []
        merged: list[dict] = []

        for path in input_paths:
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        merged.extend(data)
                    else:
                        merged.append(data)
            except Exception as e:  # noqa: BLE001
                errors.append(f"{path}: {e}")

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2)

        return ProcessingResult(
            input_file=input_paths[0] if input_paths else Path("."),
            output_file=output_path,
            records_processed=len(merged),
            errors=errors,
        )


def count_lines(path: Path) -> int:
    """Count the number of lines in a file.

    This is a pure function that takes a Path and returns a count.
    Easy to test with tmp_path fixture.
    """
    return len(path.read_text().splitlines())


def validate_json_file(path: Path) -> tuple[bool, str]:
    """Validate that a file contains valid JSON.

    Returns:
        Tuple of (is_valid, error_message).

    """
    try:
        with path.open("r", encoding="utf-8") as f:
            json.load(f)
        return (True, "")
    except json.JSONDecodeError as e:
        return (False, str(e))
    except Exception as e:  # noqa: BLE001
        return (False, f"File error: {e}")
