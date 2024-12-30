# Pytest Test Categories

A pytest plugin to enforce test timing constraints and size distributions. The test limits are taken from the book Software Engineering at Google.

## Installation

```bash
poetry install
```

## Development

This project uses Poetry for dependency management, pytest for testing, and ruff/isort for linting.

### Setup Pre-commit Hooks

```bash
poetry run pre-commit install
```

### Running Tests

```bash
poetry run pytest
```

### Linting

```bash
poetry run ruff check .
poetry run ruff format .
poetry run isort .
```
