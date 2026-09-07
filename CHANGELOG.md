# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## v1.2.2 (2026-09-07)

### Fixed

- Fix false `FilesystemAccessViolationError` (`[TC002]`) for small tests using pyfakefs's `fs` fixture under `--test-categories-enforcement=strict`. pyfakefs rebinds `pathlib`, `os`, `shutil`, and `builtins.open` in every already-imported module, including this plugin's own filesystem adapter, so the blocker was patching pyfakefs's fake classes instead of the real filesystem and misreporting purely in-memory operations as violations. The blocker now detects an active virtual filesystem and stands its own enforcement down for the duration of that test. Verified safe for the function-scoped `fs` fixture; module/class/session-scoped fixtures and the manual `Patcher()` context manager remain open gaps (#256, #257) (#254)
- Raise `pytest` minimum version to `>=9.1.1` in `pyproject.toml` and update `uv.lock` for `pytest`, `pygments`, `virtualenv`, and `filelock` to resolve reported vulnerabilities (#248)
- Fix Dependency Security Scan workflow: scope production export with `--no-dev`, use `--save-json` for artifact generation, remove `|| true` masking, allow dev scan to report without blocking, and keep `safety check` (auth-free open-source DB) until a migration to an alternative scanner is completed (#248)
- Fix CI workflow: disable Codecov CLI integrity verification (`skip_validation: true`) because Codecov's published GPG key URL is no longer available, preventing coverage upload failures (#249)

## v1.2.1 (2026-03-03)

### Fixed

- Exclude coverage.py sqlite3 data files (`.coverage`, `.coverage.*`) from database hermeticity detection, preventing false `DatabaseViolationError` when running small tests under `coverage run` (#230)

### Added

- Comprehensive enforcement demo under `examples/enforcement_demo/` showing before/after patterns for writing hermetic small tests (#221)

## v1.2.0 (2025-12-23)

### Feat

- Add auto-categorization suggestions mode (#210)
- Add per-test performance baselines (#209)
- Warn on marker inheritance conflicts (#208)

### Fix

- resolve scheduled workflow failures

## v1.1.0 (2025-12-04)

### Breaking Changes

- **Strict filesystem blocking**: Small tests now block ALL filesystem access, including `tmp_path` and `tempfile`. Use `pyfakefs` or `io.StringIO`/`io.BytesIO` for in-memory file handling in small tests. (#195)
- **Fixed time limits**: Time limits are no longer configurable. They are fixed per Google's testing standards: 1s (small), 5min (medium), 15min (large/xlarge). (#189)

### Changed

- Remediation lists in violation messages now use bullet points instead of numbered lists for consistency (#196)

### Added

- CI, coverage, and downloads badges to README (#190)
- Enhanced PyPI package metadata for better discoverability (#191)
- Mocking libraries guide and enhanced quickstart examples in documentation (#192)
- Improved `pytest --markers` descriptions with constraint details

### Fixed

- Documentation inconsistencies referencing "allowed paths" after filesystem blocking was made strict

## v1.0.0 (2025-12-01)

### Highlights

This is the first stable release of pytest-test-categories, bringing Google's battle-tested testing philosophy to Python. The plugin enforces test timing constraints, resource isolation, and validates test size distributions.

### Added

#### Resource Isolation (Hermeticity)

- **Network isolation**: Block socket connections in small tests (#72, #74, #76)
- **Filesystem isolation**: Block pathlib, os, and shutil operations in small tests (#120, #132)
- **Process isolation**: Block subprocess calls in small tests (#133)
- **Database isolation**: Block common database connections in small tests
- **Sleep blocking**: Block time.sleep() in small tests to enforce fast execution (#118)
- **Hermeticity violation tracking**: Track and report violations in terminal output (#167)
- **JSON violation reports**: Include per-type hermeticity violation breakdown in JSON reports (#169)

#### Configuration

- **Configurable distribution targets**: Customize target percentages and tolerances (#165)
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
