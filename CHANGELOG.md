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

## [0.3.0] - Unreleased

### Added
- Test coverage for failed unsized tests in detailed reports (#13)

### Changed
- Optimized plugin.py orchestration layer: reduced from 394 to 266 lines (32% reduction) by eliminating duplication and condensing docstrings (#45)
- Switch license to MIT

### Fixed
- Fixed test_base_classes_feature.py regex pattern to use re.search instead of re.match for better output matching
- Include pre-commit in lint reqs

### Improved
- Increased plugin.py test coverage from 72% to 93% through comprehensive edge case testing


## [0.1.0] - 2024-12-30
Initial release
