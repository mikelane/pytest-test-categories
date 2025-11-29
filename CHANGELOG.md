# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **JSON Report Export**: Machine-readable JSON report format for CI/CD integration (#115)
  - `--test-size-report=json` CLI option to output JSON report to terminal
  - `--test-size-report-file=PATH` CLI option to write JSON report to a file
  - JSON format includes plugin version, ISO 8601 timestamp, summary statistics, and per-test details
  - Enables CI/CD pipeline integration, dashboard visualization, and custom tooling
  - Built with Pydantic models for type-safe serialization

## [0.6.0] - 2025-11-28

### Added

- **Process Isolation**: Block subprocess spawning in small tests (#101, #108)
  - `ProcessBlockerPort` interface in `ports/process.py` following hexagonal architecture
  - `ProcessPatchingBlocker` production adapter that patches subprocess and multiprocessing
  - Intercepts `subprocess.Popen`, `subprocess.run`, `subprocess.call`, `subprocess.check_call`, `subprocess.check_output`
  - Intercepts `os.system`, `os.popen`
  - Intercepts `multiprocessing.Process`
  - `SubprocessViolationError` exception with remediation guidance
  - Architecture Decision Record (ADR-003) documenting the design

- **Database Isolation**: Block database connections in small tests (#102, #110)
  - `DatabaseBlockerPort` interface in `ports/database.py` following hexagonal architecture
  - `DatabasePatchingBlocker` production adapter that patches `sqlite3.connect`
  - `FakeDatabaseBlocker` test adapter for unit testing
  - `DatabaseViolationError` exception with remediation guidance
  - Optional support for popular database libraries (when installed):
    - PostgreSQL: `psycopg2.connect`, `psycopg.connect`
    - MySQL: `pymysql.connect`
    - MongoDB: `pymongo.MongoClient`
    - Redis: `redis.Redis`, `redis.StrictRedis`
    - SQLAlchemy: `sqlalchemy.create_engine`
  - Integration with pytest hooks for automatic enforcement on small tests
  - In-memory SQLite (`:memory:`) is blocked (stricter interpretation of hermeticity)

- **Medium Network Restriction**: Network access enforcement for medium tests (#103, #111)
  - Medium tests now restricted to localhost-only network access
  - External network connections blocked for medium tests in strict/warn modes
  - `NetworkMode` enum added to `types.py` with values: `BLOCK_ALL`, `LOCALHOST_ONLY`, `ALLOW_ALL`
  - `TestSize.network_mode` property maps test sizes to appropriate network modes:
    - Small: `BLOCK_ALL` (no network access)
    - Medium: `LOCALHOST_ONLY` (localhost only)
    - Large/XLarge: `ALLOW_ALL` (full network access)
  - Follows Google's "Software Engineering at Google" test size definitions

- **Distribution Enforcement**: New enforcement modes for test distribution validation (#104, #109)
  - `--test-categories-distribution-enforcement` CLI option with choices: `off`, `warn`, `strict`
  - `test_categories_distribution_enforcement` ini option for configuration
  - `off` mode: Skip validation entirely (default, backwards compatible)
  - `warn` mode: Emit warnings but allow build to continue
  - `strict` mode: Fail collection if distribution is outside acceptable range
  - Actionable error messages with current distribution, targets, and remediation guidance
  - `DistributionValidationService` for pure domain logic with hexagonal architecture
  - Comprehensive user documentation with examples for each mode

- **Thread Monitoring**: Warn when small tests use threading primitives (#105, #112)
  - `ThreadMonitorPort` interface defined in `ports/threading.py`
  - Production adapter `ThreadPatchingMonitor` in `adapters/threading.py`
  - Test adapter `FakeThreadMonitor` in `adapters/fake_threading.py`
  - Monitors `threading.Thread`, `threading.Timer`, `concurrent.futures.ThreadPoolExecutor`, and `concurrent.futures.ProcessPoolExecutor`
  - Unlike other blockers, thread monitoring WARNS instead of blocking because:
    - Many libraries use threading internally (logging, garbage collection)
    - Some test frameworks use threading
    - Blocking threading could break legitimate test infrastructure
  - Warning message includes test name and suggests using `@pytest.mark.medium`
  - No impact on medium/large/xlarge tests (threading is expected for those sizes)

- **Strict Enforcement Dogfooding**: Enable strict enforcement in project itself (#106, #107)
  - Project now uses its own strict enforcement mode
  - Validates the plugin works correctly on real-world codebase

### Fixed

- Recategorized pytester tests from small to medium (#99)

## [0.5.0] - 2025-11-28

> **Note**: This version was tagged for git history but not released to PyPI.
> The features listed here are included in v0.6.0.

### Added

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
