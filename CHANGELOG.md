# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - TBD

### Added

- **Process Isolation**: New `SubprocessViolationError` exception and `ProcessBlockerPort` interface for blocking subprocess spawning in small tests (#101)
  - Intercepts `subprocess.Popen`, `subprocess.run`, `subprocess.call`, `subprocess.check_call`, `subprocess.check_output`
  - Intercepts `os.system`, `os.popen`
  - Intercepts `multiprocessing.Process`
  - Provides actionable error messages with remediation guidance
  - Architecture Decision Record (ADR-003) documenting the design
- **Filesystem Isolation Design**: Architecture Decision Record (ADR-002) documenting the design for filesystem isolation in small tests (#91, #95)
- **Filesystem Isolation Documentation**: Comprehensive documentation for the filesystem isolation feature including:
  - User guide explaining filesystem isolation concepts and usage (#94)
  - Troubleshooting guide for filesystem violations (#94)
  - Examples demonstrating common patterns and fixes (#94)
  - Configuration reference for allowed paths (#94)
- **Configuration Options**: New configuration options for filesystem isolation (planned implementation):
  - `test_categories_allowed_paths` ini option for configuring allowed filesystem paths
  - `--test-categories-allowed-paths` CLI option for command-line configuration
  - Per-test markers `@pytest.mark.allow_filesystem` and `@pytest.mark.allow_filesystem_paths` (planned)

### Documentation

- Updated user guide index with filesystem isolation information
- Updated troubleshooting index with filesystem violations guide
- Updated examples index with filesystem isolation examples
- Updated configuration reference with new filesystem options
- Added filesystem column to test size markers quick reference table

## [0.4.0] - 2025-11-27

### BREAKING CHANGE

- The plugin now requires session-specific state management, which may affect existing configurations.

### Feat

- Integrate network blocking with pytest hooks (#76)
- Implement NetworkBlockerPort adapters for network isolation (#74)
- Add NetworkBlockerPort interface for network isolation (#72)
- Add world-class CI/CD infrastructure with automated PyPI publishing (#21)
- **infra**: add GitHub workflow infrastructure and project documentation
- **pytest_test_categories**: enhance test size reporting and update dependencies
- **test-categories**: enhance test timing and distribution analysis
- **test-categorization**: enhance test size distribution and reporting
- add LICENSE and enhance README for Pytest Test Categories Plugin
- **plugin**: enhance test distribution validation
- **distribution**: enhance test distribution validation
- **distribution**: add test distribution statistics tracking
- **plugin**: add timing validation for test categories
- **test-categories**: add test timing and violation handling
- **plugin**: enhance test categories with Pydantic and StrEnum
- **plugin**: add warning for tests without size markers
- **plugin**: add error for multiple size markers in tests
- **plugin**: add LARGE and XLARGE test size categories
- **test-categories**: enhance test size categorization
- add pytest plugin for test timing constraints

### Fix

- **ci**: Remove auto-approve step from dependabot workflow (#33)
- **ci**: Remove conflicting CodeQL workflow (use default setup) (#31)
- **dev**: include pre-commit in lint reqs

### Refactor

- Convert plugin.py to pure orchestration layer (#60)
- **plugin**: move TestSize enum to types module
