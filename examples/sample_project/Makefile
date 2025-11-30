# Sample Project Makefile
# =======================
#
# Common commands for working with the sample project.
# Run `make help` to see available targets.

.PHONY: help install test test-small test-medium test-large coverage lint format clean

# Default target
help:
	@echo "Sample Project - pytest-test-categories Example"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Setup:"
	@echo "  install        Install all dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  test           Run all tests"
	@echo "  test-small     Run only small tests (fast, hermetic)"
	@echo "  test-medium    Run only medium tests (localhost, containers)"
	@echo "  test-large     Run only large tests (integration)"
	@echo "  test-strict    Run all tests with strict enforcement"
	@echo "  test-report    Run tests with detailed report"
	@echo "  test-json      Run tests and generate JSON report"
	@echo ""
	@echo "Coverage:"
	@echo "  coverage       Run tests with coverage report"
	@echo "  coverage-html  Generate HTML coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint           Run linter (ruff check)"
	@echo "  format         Format code (ruff format)"
	@echo "  check          Run all quality checks"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean          Remove build artifacts and caches"

# ==============================================================================
# Setup
# ==============================================================================

install:
	uv sync --all-extras

# ==============================================================================
# Testing
# ==============================================================================

test:
	uv run pytest

test-small:
	uv run pytest -m small -v

test-medium:
	uv run pytest -m medium -v

test-large:
	uv run pytest -m large -v

test-strict:
	uv run pytest --test-categories-enforcement=strict

test-report:
	uv run pytest --test-size-report=detailed

test-json:
	uv run pytest --test-size-report=json --test-size-report-file=test-report.json
	@echo ""
	@echo "JSON report written to: test-report.json"

# ==============================================================================
# Coverage
# ==============================================================================

coverage:
	uv run coverage run -m pytest
	uv run coverage report --show-missing

coverage-html:
	uv run coverage run -m pytest
	uv run coverage html
	@echo ""
	@echo "HTML coverage report: htmlcov/index.html"

# ==============================================================================
# Code Quality
# ==============================================================================

lint:
	uv run ruff check src tests

format:
	uv run ruff format src tests
	uv run ruff check --fix src tests

check: lint
	uv run mypy src

# ==============================================================================
# Cleanup
# ==============================================================================

clean:
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf .ruff_cache
	rm -rf .mypy_cache
	rm -rf test-report.json
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
