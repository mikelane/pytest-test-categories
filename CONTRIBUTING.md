# Contributing to pytest-test-categories

Thank you for your interest in contributing to pytest-test-categories! This document provides comprehensive guidelines for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Documentation Standards](#documentation-standards)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Pull Request Process](#pull-request-process)
- [Issue Guidelines](#issue-guidelines)
- [Release Process](#release-process)

## Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow. Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing.

## Getting Started

### Prerequisites

- Python 3.11 or higher (3.12 recommended)
- [uv](https://github.com/astral-sh/uv) for fast dependency management
- Git
- GitHub CLI (`gh`) recommended for workflow automation

### Repository Security Configuration

**For maintainers with admin access**: This repository uses **CodeQL Advanced Setup** for security scanning, which requires manual configuration in GitHub settings.

**IMPORTANT**: Before the security workflow can run successfully, you must disable GitHub's default CodeQL setup:

1. Go to: **Settings → Code security and analysis**
2. Find: **"CodeQL analysis"** under "Code scanning"
3. Click: **Configure** or the three dots menu (⋯)
4. Select: **"Disable CodeQL"**

For detailed instructions and troubleshooting, see [`.github/CODEQL_SETUP.md`](.github/CODEQL_SETUP.md).

**Why this matters**: GitHub does not allow both default and advanced CodeQL configurations to run simultaneously. Our advanced setup provides extended security queries and integration with our CI/CD pipeline, but will fail with the error "CodeQL analyses from advanced configurations cannot be processed when the default setup is enabled" if default setup is still active.

### Fork and Clone

1. Fork the repository using GitHub CLI:
   ```bash
   gh repo fork mikelane/pytest-test-categories --clone --remote
   cd pytest-test-categories
   ```

2. Set up your development environment:
   ```bash
   uv sync --all-groups
   uv run pre-commit install
   ```

### Verify Installation

Run the test suite to ensure everything is set up correctly:

```bash
uv run pytest
```

All tests should pass, and coverage should be at 100%.

## Development Workflow

### 1. Create an Issue First

**All work must be tracked through GitHub issues.** Before starting any work:

1. Search existing issues to avoid duplicates
2. Create a new issue using the appropriate template:
   - **Bug Report**: For reporting bugs or unexpected behavior
   - **Feature Request**: For suggesting new features
   - **Documentation**: For documentation improvements
   - **Performance**: For performance improvements
   - **Refactoring**: For code quality improvements
   - **Test Improvement**: For test coverage or quality improvements

3. Wait for maintainer feedback before starting work on major changes
4. Assign yourself to the issue when you begin work

### 2. Create a Feature Branch

Never commit directly to `main`. Create a descriptive feature branch:

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
# or
git checkout -b docs/documentation-improvement
```

Branch naming conventions:
- `feature/*` - New features
- `fix/*` - Bug fixes
- `docs/*` - Documentation only
- `refactor/*` - Code refactoring
- `test/*` - Test improvements
- `perf/*` - Performance improvements

### 3. Follow TDD (Test-Driven Development)

This project strictly follows TDD principles:

1. **Write the test first** - Before implementing any feature or fix
2. **Watch it fail** - Ensure the test fails for the right reason
3. **Write minimal code** - Make the test pass with the simplest implementation
4. **Refactor** - Improve the code while keeping tests green
5. **Repeat** - Continue the red-green-refactor cycle

### 4. Make Your Changes

Follow these guidelines:
- Keep changes focused and atomic
- Maintain or improve test coverage (100% required)
- Update documentation in the same commit as code changes
- Follow the coding standards (see below)
- Run pre-commit hooks before committing

### 5. Run Tests and Quality Checks

This project uses [tox](https://tox.wiki/) for multi-version testing:

```bash
# Run fast parallel tests (used by pre-commit)
uv run tox run-parallel -e py311-fast,py312-fast,py313-fast,py314-fast

# Run full test suite across all Python versions
uv run tox

# Test a specific Python version
uv run tox -e py312

# Run tests directly with pytest
uv run pytest

# Run with coverage
uv run coverage run -m pytest
uv run coverage report
```

Pre-commit hooks ensure code quality:

```bash
# Run all hooks manually
uv run pre-commit run --all-files

# Individual checks
uv run isort .
uv run ruff check --fix .
uv run ruff format .
```

### 6. Commit Your Changes

Follow conventional commit format (see [Commit Message Guidelines](#commit-message-guidelines)):

```bash
git add <specific-files>  # Never use -A or --all
git commit -m "feat: add custom time limit configuration"
```

### 7. Keep Your Branch Updated

Regularly sync with the main branch:

```bash
git fetch origin
git rebase origin/main
```

### 8. Push and Create Pull Request

```bash
git push origin your-branch-name
gh pr create --title "Your PR title" --body "Fixes #issue-number"
```

See [Pull Request Process](#pull-request-process) for details.

## Coding Standards

### Python Style

- **Line length**: 120 characters
- **Quote style**: Single quotes for inline strings, double quotes for docstrings
- **Type hints**: Required for all public APIs
- **Imports**: Must include `from __future__ import annotations` at the top of every file

### Code Quality Tools

All code must pass:
- **Ruff**: Linting and formatting
- **isort**: Import sorting
- **Type checking**: Beartype for runtime type checking
- **Pre-commit hooks**: All hooks must pass

Configuration is in `pyproject.toml`.

### Design Principles

- **SOLID Principles**: Follow Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, and Dependency Inversion
- **Clean Code**: Prefer clarity over cleverness
- **Separation of Concerns**: Each module should have a single, well-defined purpose
- **Design by Contract**: Use `icontract` for preconditions and postconditions where appropriate
- **Type Safety**: Use Pydantic models for data validation

### Naming Conventions

#### Test Naming
- **Avoid "should"**: Use "It returns email" not "It should return email"
- **Be specific**: Describe the actual behavior being tested
- **Test files**: `test_*.py` or `it_*.py`
- **Test functions**: `test_*` or `it_*`
- **Test classes**: `Describe[A-Z]*` (RSpec-style)

#### Code Naming
- **Functions/Methods**: `snake_case`, verb phrases (e.g., `validate_distribution`)
- **Classes**: `PascalCase`, noun phrases (e.g., `TestTimer`)
- **Constants**: `UPPER_SNAKE_CASE`
- **Private members**: Prefix with `_` (e.g., `_internal_state`)

### File Organization

```
src/pytest_test_categories/
├── __init__.py           # Package exports
├── plugin.py             # Pytest integration and hooks
├── types.py              # Core domain types
├── timing.py             # Time limit configuration
├── timers.py             # Timer implementations
├── reporting.py          # Test size reporting
├── distribution/
│   ├── __init__.py
│   └── stats.py          # Distribution validation
└── test_bases.py         # Base test classes
```

## Testing Requirements

### Coverage Requirements

- **100% test coverage** is required for all new code
- Coverage is verified by CI and pre-commit hooks
- Coverage target is defined in `coverage_target.txt`

### Test Organization

Tests are organized by:
- **Feature tests** (`test_*_feature.py`): End-to-end behavior validation
- **Module tests** (`test_*_module.py`): Individual component validation

### Test Quality Standards

- **Keep tests simple**: Avoid loops, branching, and complex logic in tests
- **Use parametrization**: Instead of loops in tests, use `@pytest.mark.parametrize`
- **One assertion per concept**: Tests should verify one behavior
- **Arrange-Act-Assert**: Follow the AAA pattern
- **Deterministic**: Tests must not be flaky
- **Fast**: Test suite should remain fast (under 30 seconds total)

### Testing the Plugin

Use pytest's `pytester` fixture for testing the plugin:

```python
def test_timing_violation(pytester):
    """It fails tests that exceed time limits."""
    pytester.makepyfile("""
        import pytest
        import time

        @pytest.mark.small
        def test_slow():
            time.sleep(2)  # Exceeds 1s limit
    """)
    result = pytester.runpytest()
    result.assert_outcomes(failed=1)
```

## Documentation Standards

### Synchronization Requirement

**Critical**: Documentation must be updated in the same commit as code changes. This includes:

- **README.md**: User-facing documentation
- **CLAUDE.md**: Architecture and development documentation
- **Docstrings**: API documentation
- **CHANGELOG.md**: Release notes
- **Code comments**: Complex logic explanations

### Docstring Format

Use Google-style docstrings:

```python
def validate_distribution(stats: DistributionStats) -> None:
    """Validate that test distribution meets target percentages.

    Args:
        stats: Distribution statistics to validate.

    Raises:
        ValueError: If distribution falls outside acceptable ranges.

    Examples:
        >>> stats = DistributionStats(small=80, medium=15, large=5)
        >>> validate_distribution(stats)  # Passes
    """
```

### Documentation Types

1. **API Documentation**: Comprehensive docstrings for public APIs
2. **Architecture Documentation**: Design decisions in CLAUDE.md
3. **User Documentation**: Usage examples in README.md
4. **Change Documentation**: All changes in CHANGELOG.md
5. **Code Comments**: Complex algorithms and non-obvious decisions

## Commit Message Guidelines

### Conventional Commits Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `test`: Test improvements
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `build`: Build system changes
- `ci`: CI/CD changes
- `chore`: Maintenance tasks

### Scope (Optional)

- `plugin`: Plugin hooks and integration
- `timing`: Timing enforcement
- `distribution`: Distribution validation
- `reporting`: Test size reporting
- `types`: Type definitions
- `docs`: Documentation
- `ci`: CI/CD

### Subject

- Use imperative mood: "add" not "added" or "adds"
- Don't capitalize first letter
- No period at the end
- Maximum 72 characters

### Body (Optional)

- Explain what and why, not how
- Wrap at 72 characters
- Separate from subject with blank line

### Footer (Optional)

- Reference issues: `Fixes #123` or `Closes #456`
- Breaking changes: `BREAKING CHANGE: description`

### Examples

```
feat(timing): add configurable time limits

Allow users to override default time limits via pytest configuration.

Fixes #42
```

```
fix(plugin): prevent timer state corruption in parallel execution

Timer state was being shared across parallel test execution,
causing race conditions. Added per-test timer isolation.

Fixes #78
```

```
docs: update README with custom configuration examples

Add examples showing how to configure custom time limits
in pyproject.toml and pytest.ini.
```

### Important Notes

- **No attribution lines**: Do not add "Co-Authored-By" or attribution lines
- **Explicit staging**: Never use `git add -A` or `git add --all` - stage files explicitly
- **Keep commits atomic**: One logical change per commit

## Pull Request Process

### Before Opening a PR

1. Ensure all tests pass: `uv run tox` or `uv run pytest`
2. Ensure all pre-commit hooks pass: `uv run pre-commit run --all-files`
3. Verify 100% coverage: `uv run python tests/_utils/check_coverage.py`
4. Update CHANGELOG.md with your changes
5. Ensure documentation is synchronized with code changes

### Creating the PR

1. Use a descriptive title that summarizes the change
2. Reference the issue: `Fixes #issue-number` in the description
3. Fill out the PR template completely
4. Mark the PR as draft if it's work-in-progress
5. Request review from maintainers

### PR Description

A good PR description includes:

- **Summary**: What does this PR do?
- **Motivation**: Why is this change needed?
- **Implementation**: How is it implemented (high-level)?
- **Testing**: What testing was done?
- **Documentation**: What documentation was updated?
- **Breaking Changes**: Any breaking changes?

### PR Review Process

1. **Automated Checks**: CI must pass (tests, linting, coverage)
2. **Code Review**: Maintainer reviews for:
   - Code quality and design
   - Test coverage and quality
   - Documentation completeness
   - SOLID principles adherence
3. **Feedback**: Address review comments promptly
4. **Approval**: PR must be approved before merging
5. **Merge**: Maintainer merges using squash or merge commit

### During Review

- Be responsive to feedback
- Push additional commits to address review comments
- Update the PR description if scope changes
- Keep the PR focused - avoid scope creep

### After Merge

- Delete your feature branch
- Close related issues (if not auto-closed)
- Monitor for any issues in production

## Issue Guidelines

### Before Creating an Issue

1. Search existing issues to avoid duplicates
2. Check if the issue is already fixed in `main`
3. Gather relevant information (versions, logs, examples)

### Creating a Good Issue

1. **Use the appropriate template**: Choose the template that best matches your issue type
2. **Be specific**: Provide exact steps to reproduce, expected vs. actual behavior
3. **Provide context**: Include version information, environment details
4. **Include examples**: Code snippets, error messages, logs
5. **One issue per problem**: Don't combine multiple unrelated issues

### Issue Labels

Issues are automatically labeled based on the template, but maintainers may add additional labels:

- **Priority**: `priority-critical`, `priority-high`, `priority-medium`, `priority-low`
- **Status**: `triage`, `accepted`, `in-progress`, `blocked`, `wontfix`
- **Type**: `bug`, `enhancement`, `documentation`, `performance`, `refactoring`, `testing`
- **Area**: `plugin`, `timing`, `distribution`, `reporting`, `ci`
- **Special**: `good-first-issue`, `help-wanted`, `breaking-change`

### Issue Lifecycle

1. **Triage**: Maintainer reviews and labels the issue
2. **Accepted**: Issue is approved for work
3. **In Progress**: Someone is actively working on it
4. **PR Opened**: Pull request addresses the issue
5. **Closed**: Issue is resolved or declined

## Release Process

This section is primarily for maintainers, but contributors should understand the release workflow.

### Versioning

This project uses [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes (e.g., 1.0.0 → 2.0.0)
- **MINOR**: New features, backward compatible (e.g., 1.0.0 → 1.1.0)
- **PATCH**: Bug fixes, backward compatible (e.g., 1.0.0 → 1.0.1)

### Release Workflow

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md with release notes
3. Create release commit: `chore: release v1.2.0`
4. Tag the release: `git tag -a v1.2.0 -m "Release v1.2.0"`
5. Push tag: `git push origin v1.2.0`
6. GitHub Actions builds and publishes to PyPI
7. Create GitHub release with changelog

### CHANGELOG.md

Maintain CHANGELOG.md following [Keep a Changelog](https://keepachangelog.com/):

```markdown
## [Unreleased]

### Added
- New feature X (#123)

### Changed
- Improved Y (#124)

### Fixed
- Bug Z (#125)

## [1.2.0] - 2024-01-15

### Added
- Custom time limit configuration (#42)
```

## Getting Help

### Resources

- **Documentation**: [README.md](README.md)
- **Architecture Guide**: [CLAUDE.md](CLAUDE.md)
- **Issue Templates**: Use these for common scenarios
- **Discussions**: Ask questions in GitHub Discussions

### Communication

- **Questions**: Use GitHub Discussions
- **Bugs**: Open a bug report issue
- **Features**: Open a feature request issue
- **Security**: See [SECURITY.md](SECURITY.md)

### Community

- Be respectful and constructive
- Help others when you can
- Share your knowledge
- Give credit to contributors

## Recognition

Contributors are recognized in:
- CHANGELOG.md for their contributions
- GitHub contributors page
- Release notes

Thank you for contributing to pytest-test-categories! Your contributions help make testing better for everyone.
