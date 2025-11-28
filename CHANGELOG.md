# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - In Progress

### Added
- **Network isolation enforcement via pytest hooks** (#69, #70)
  - `--test-categories-enforcement` CLI option with values: `off`, `warn`, `strict`
  - `test_categories_enforcement` ini option in pyproject.toml
  - Blocks network access for small tests when enforcement is enabled
  - Socket patching to intercept connection attempts
  - Proper cleanup to restore socket behavior after each test
- `NetworkBlockerPort` interface following hexagonal architecture (PR #74)
- `SocketPatchingNetworkBlocker` adapter for network isolation (PR #74)
- `HermeticityViolationError` exception hierarchy for resource violations (PR #74)
- `NetworkAccessViolationError` with detailed remediation guidance (PR #74)
- `EnforcementMode` enum for configuration (PR #74)
- Comprehensive documentation for network isolation (PR #75):
  - User guide: `docs/user-guide/network-isolation.md`
  - Troubleshooting: `docs/troubleshooting/network-violations.md`
  - Examples: `docs/examples/network-isolation.md`
  - ADR: `docs/architecture/adr-001-network-isolation.md`

### Changed
- Small tests now have network access blocked when enforcement is `strict` or `warn`
- Medium, large, and xlarge tests are not affected by network blocking

Initial release

## v0.4.0 (2025-11-27)

### BREAKING CHANGE

- The plugin now requires session-specific state
management, which may affect existing configurations.

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
