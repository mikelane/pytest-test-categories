# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## v1.0.0 (2025-12-01)

### Highlights

This is the first stable release of pytest-test-categories, bringing Google's battle-tested testing philosophy to Python. The plugin enforces test timing constraints, resource isolation, and validates test size distributions.

### Added

#### Resource Isolation (Hermeticity)

- **Network isolation**: Block socket connections in small tests (#72, #74, #76)
- **Filesystem isolation**: Block pathlib, os, and shutil operations outside allowed paths (#120, #132)
- **Process isolation**: Block subprocess calls in small tests (#133)
- **Database isolation**: Block common database connections in small tests
- **Sleep blocking**: Block time.sleep() in small tests to enforce fast execution (#118)
- **Hermeticity violation tracking**: Track and report violations in terminal output (#167)
- **JSON violation reports**: Include per-type hermeticity violation breakdown in JSON reports (#169)

#### Configuration

- **Configurable time limits**: Set custom time limits per test size category (#117)
- **Configurable distribution targets**: Customize target percentages and tolerances (#165)
- **Allowed paths**: Configure additional allowed filesystem paths for small tests
- **Enforcement modes**: Choose between `off`, `warn`, and `strict` enforcement

#### Reporting

- **JSON report export**: Machine-readable reports for CI/CD integration (#116)
- **Test size reports**: Basic and detailed terminal reports
- **Distribution validation**: Warn or fail when test pyramid is inverted

#### Parallel Execution

- **pytest-xdist support**: Full compatibility with parallel test execution (#131, #139)
  - Distribution stats aggregated correctly across workers
  - Test reports merged from all workers on controller
  - Timer isolation ensures no race conditions between workers
- **Comprehensive xdist edge case tests**: Validate behavior under various parallel scenarios (#164)

#### Documentation

- Comprehensive API reference with error codes and remediation guidance (#134, #147)
- User guide covering all isolation types (#144)
- Architecture documentation with design philosophy and ADRs (#145)
- Migration guide, common patterns, and CI integration examples (#146)
- IDE integration guide for PyCharm and VS Code (#137)
- Ecosystem integration guides for popular testing libraries (#154)
- Example project demonstrating best practices (#126, #138)

#### Developer Experience

- **Base test classes**: Inherit from `SmallTest`, `MediumTest`, `LargeTest`, or `XLargeTest`
- **External systems warning**: Guidance when medium tests use Docker/testcontainers (#119, #133)
- **Centralized error registry**: Consistent error codes with actionable remediation (#134)
- **Performance benchmarks**: Validated zero-overhead claims (<1% impact) (#127, #135)

#### Infrastructure

- World-class CI/CD with automated PyPI publishing (#21)
- Python 3.11, 3.12, 3.13, 3.14 support
- 100% test coverage enforcement
- Security audit completed (#136)

### Changed

- Plugin architecture refactored to hexagonal/ports-and-adapters pattern (#60)
- TestSize enum moved to dedicated types module

### Breaking Changes

- The plugin now requires session-specific state management
- `ViolationsSummary.hermeticity` changed from `int` to `HermeticityViolationsSummary` object with per-type breakdown

## v0.7.0 (2025-11-29)

### Added

- Add sleep blocking for small tests (#118)
- Add configurable time limits for test size categories (#117)
- Add JSON report export for CI integration (#116)

### Fixed

- Add Python 3.14 to release workflow test matrix

## v0.6.0 (2025-11-28)

### Fixed

- Add shell: bash to Verify plugin registration step
- Update __version__ to 0.6.0 in __init__.py
- Recategorize pytester tests from small to medium (#99)

## v0.5.0 (2025-11-28)

Initial public release with core functionality.

## v0.4.0 (2025-11-27)

### Added

- Network blocking integration with pytest hooks (#76)
- NetworkBlockerPort adapters for network isolation (#74)
- NetworkBlockerPort interface for network isolation (#72)
- CI/CD infrastructure with automated PyPI publishing (#21)
- Test distribution validation and statistics tracking
- Timing validation for test categories
- Warning for tests without size markers
- Error for multiple size markers in tests
- LARGE and XLARGE test size categories
- Basic pytest plugin for test timing constraints

### Fixed

- Remove auto-approve step from dependabot workflow (#33)
- Remove conflicting CodeQL workflow (#31)

### Changed

- Convert plugin.py to pure orchestration layer (#60)
- Move TestSize enum to types module
