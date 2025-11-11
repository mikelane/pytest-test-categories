# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a pytest plugin that enforces test timing constraints and validates test size distributions based on Google's "Software Engineering at Google" best practices. The plugin categorizes tests into four sizes (small, medium, large, xlarge) with specific time limits and tracks whether the test suite meets target distribution percentages.

## Agent Workflow Requirements

**CRITICAL: All agents working on this repository MUST follow these requirements:**

1. **GitHub Issue Required**: Create a GitHub issue for ALL work before starting implementation
   - Use descriptive titles and comprehensive descriptions
   - Add appropriate labels (bug, enhancement, documentation, etc.)
   - Reference related issues if applicable
   - Keep the issue updated with progress, blockers, and decisions

2. **Pull Request Required**: ALL changes MUST go through a Pull Request
   - Never commit directly to main branch
   - Create a feature branch for your work
   - Open a PR as soon as you have commits to share
   - Link the PR to the issue (use "Fixes #issue-number" in PR description)
   - Keep PR description updated with implementation details and testing notes

3. **Continuous Updates**: Keep issue and PR updated throughout development
   - Comment on the issue when starting work, encountering blockers, or making decisions
   - Update PR description as implementation evolves
   - Push commits frequently to keep PR current
   - Respond to review comments promptly

4. **Documentation Maintenance**: Keep documentation synchronized with code changes
   - Update relevant documentation in the SAME commit as code changes
   - This includes: README.md, CHANGELOG.md, docstrings, and this CLAUDE.md
   - Documentation is code - treat it with the same rigor
   - Never merge a PR with outdated documentation

## Development Commands

### Installation
```bash
# Install all dependencies (development and production)
uv sync --all-groups
```

### Pre-commit Setup
```bash
# Install pre-commit hooks
uv run pre-commit install

# Run all pre-commit hooks manually
uv run pre-commit run --all-files
```

### Testing Commands

**Coverage Note**: This project uses `coverage run` instead of `pytest --cov` because pytest loads plugins before coverage tracking starts. Using `coverage run -m pytest` ensures all module-level code (imports, class definitions, decorators) is tracked correctly.

**Tox for Multi-Version Testing**: Use tox to test against all supported Python versions (3.11, 3.12, 3.13, 3.14) in isolated environments.

```bash
# Run tests across all Python versions with tox (full output, verbose)
uv run tox

# Run tests for a specific Python version
uv run tox -e py312

# Run tests in parallel across all versions (fast, minimal output)
uv run tox run-parallel

# Run fast parallel tests (used by pre-commit, with pytest-xdist)
uv run tox run-parallel -e py311-fast,py312-fast,py313-fast,py314-fast

# List all available tox environments
uv run tox list

# Run all tests with coverage (single version)
uv run coverage run -m pytest

# Run tests in parallel with pytest-xdist (single version)
uv run pytest -n auto

# View coverage report in terminal
uv run coverage report

# View detailed coverage with missing lines
uv run coverage report --show-missing

# Generate XML coverage report (for codecov)
uv run coverage xml

# Generate HTML coverage report for local viewing
uv run coverage html

# Run a single test file (without coverage)
uv run pytest tests/test_plugin_module.py

# Run a single test function (without coverage)
uv run pytest tests/test_plugin_module.py::test_function_name

# Run a specific test class (without coverage)
uv run pytest tests/test_plugin_module.py::DescribeClass

# Run tests with detailed output (without coverage)
uv run pytest -vv
```

### Code Quality
```bash
# Run isort (import sorting)
uv run isort .

# Run ruff check with auto-fix
uv run ruff check --fix .

# Run ruff format
uv run ruff format .
```

### Coverage Validation
```bash
# Check that coverage meets the target (100% by default)
uv run python tests/_utils/check_coverage.py
```

The coverage target is stored in `coverage_target.txt` (currently 100.0).

## Architecture

### Core Components

**Plugin Entry Point** (`src/pytest_test_categories/plugin.py`)
- Implements pytest hooks to integrate with pytest's test lifecycle
- Manages session state via `PluginState` (active status, timer, distribution stats, warnings, reports)
- Key hooks:
  - `pytest_configure`: Registers size markers and initializes plugin state
  - `pytest_collection_modifyitems`: Counts tests by size and appends size labels to test IDs
  - `pytest_collection_finish`: Validates test distribution after collection
  - `pytest_runtest_protocol`: Tracks test timing with WallTimer
  - `pytest_runtest_makereport`: Validates timing constraints and updates test reports
  - `pytest_terminal_summary`: Displays distribution summary and optional size reports

**Test Size System** (`src/pytest_test_categories/types.py`)
- `TestSize` enum: Defines four size categories (SMALL, MEDIUM, LARGE, XLARGE)
- `TestTimer` abstract base class: Interface for timing implementations with state machine (READY → RUNNING → STOPPED)
- Uses `icontract` for design-by-contract preconditions/postconditions on timer state transitions

**Timing Enforcement** (`src/pytest_test_categories/timing.py`)
- `TimeLimit` model: Immutable configuration for time limits (frozen Pydantic model)
- Time limits: Small (1s), Medium (300s), Large/XLarge (900s)
- `validate()`: Raises `TimingViolationError` if test exceeds its size's limit

**Timer Implementation** (`src/pytest_test_categories/timers.py`)
- `WallTimer`: Concrete implementation using wall-clock time
- Enforces state transitions through contracts

**Distribution Validation** (`src/pytest_test_categories/distribution/stats.py`)
- `DistributionStats`: Tracks test counts and calculates percentages
- Target distribution: 80% small (±5%), 15% medium (±5%), 5% large/xlarge (±3%)
- `validate_distribution()`: Raises ValueError if distribution falls outside acceptable ranges

**Test Reporting** (`src/pytest_test_categories/reporting.py`)
- `TestSizeReport`: Collects test outcomes and durations
- Supports `--test-size-report=basic|detailed` command-line option
- Basic report: Summary statistics by size
- Detailed report: Individual test listings with outcomes and timings

**Base Test Classes** (`src/pytest_test_categories/test_bases.py`)
- Provides base classes users can inherit from: `SmallTest`, `MediumTest`, `LargeTest`, `XLargeTest`
- Each class applies the appropriate pytest marker automatically

### Design Patterns

**State Management**
- Plugin state is stored on the pytest Config object (`config._test_categories_state`)
- Pydantic models ensure type safety and validation
- Timer uses state machine pattern with contract enforcement

**Hook-Based Architecture**
- Plugin integrates through pytest's hook system
- Uses `@pytest.hookimpl` decorators with `tryfirst=True` for priority hooks
- Hook wrappers (`hookwrapper=True`) allow pre/post processing around pytest operations

**Separation of Concerns**
- `plugin.py`: Pytest integration and orchestration
- `types.py`: Core domain types and abstractions
- `timing.py`: Time limit configuration and validation logic
- `timers.py`: Timing implementations
- `distribution/`: Distribution analysis and validation
- `reporting.py`: Test size reporting

### Testing Strategy

**Test Organization**
- Tests are organized by feature (`test_*_feature.py`) and module (`test_*_module.py`)
- Feature tests validate end-to-end behavior
- Module tests validate individual components
- Uses pytest's `pytester` fixture for testing the plugin itself

**Test Configuration** (`pyproject.toml`)
- Test discovery: Files matching `it_*.py` or `test_*.py`
- Test functions: Matching `it_*` pattern
- Test classes: Matching `Describe[A-Z]*` pattern (RSpec-style naming)
- Pytest paths: `["src", "tests/plugins"]`
- Coverage: Configured to measure `src` directory

**Naming Convention**
- Avoid "should" in test names (e.g., "It returns email" not "It should return email")
- Keep tests simple - avoid loops, branching, or complex logic in tests
- Use parametrization instead of loops when possible

### Code Quality Standards

**Formatting and Linting** (configured in `pyproject.toml`)
- Ruff: Line length 120, Python 3.12 target
- Single quotes for inline strings, double quotes for docstrings
- Isort: Black-compatible profile with forced grid wrap
- All Python files must start with `from __future__ import annotations`

**Type Safety**
- Uses Pydantic for runtime validation
- Uses beartype for runtime type checking
- Uses icontract for design-by-contract

**Coverage Requirements**
- Target: 100% coverage (defined in `coverage_target.txt`)
- Enforced via `tests/_utils/check_coverage.py` utility

### Key Implementation Details

**Size Marker Detection**
- Markers are registered dynamically from `TestSize` enum
- Tests can only have one size marker (enforced by `_iter_sized_items`)
- Missing markers trigger warnings (tracked to avoid duplicate warnings)

**Test ID Modification**
- Plugin appends size labels (e.g., `[SMALL]`) to test node IDs during collection
- Done in `pytest_collection_modifyitems` by modifying `item._nodeid`

**Timer Integration**
- Timer starts in `pytest_runtest_protocol` (wrapper hook)
- Timer stops in finally block to ensure cleanup even on failure
- Duration extracted from timer or report depending on availability
- Only validates timing for tests in 'call' phase (not setup/teardown)

**Distribution Warnings**
- Critical thresholds: <50% small tests, >8% large/xlarge, >20% medium
- Provides actionable guidance for improving distribution
- Status message prioritizes most severe deviation

## Common Development Tasks

When implementing new features:
1. **Create GitHub issue first** - describe the feature, acceptance criteria, and approach
2. **Create feature branch** - use descriptive branch names (e.g., `feature/add-timeout-config`)
3. **Start with tests** - this project follows TDD
4. **Add type annotations** - use Pydantic/beartype for validation
5. **Update documentation** - in the same commits as code changes
6. **Open PR early** - link to issue, keep description updated
7. **Update CHANGELOG.md** - follow the existing format
8. **Run pre-commit hooks** - before pushing commits
9. **Ensure 100% test coverage** - verified by pre-commit
10. **Keep issue/PR updated** - comment on progress, blockers, decisions

When modifying the plugin:
- Be careful with pytest hook ordering (use `tryfirst=True` when needed)
- Session state must be thread-safe for parallel test execution
- Timer state must be reset between tests
- Distribution validation happens after collection, not during execution
- do not add attribution or co-authored lines to commits.
