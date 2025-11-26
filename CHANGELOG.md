# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - Unreleased

### Added
- **Network isolation enforcement for hermetic tests** (#70)
  - Block network access for small tests to ensure hermeticity
  - Allow localhost-only access for medium tests
  - Full network access for large/xlarge tests
- New `test_categories_enforcement` configuration option
  - `strict`: Fail tests immediately on network violations
  - `warn`: Emit warnings but allow tests to continue
  - `off`: Disable enforcement entirely
- New `@pytest.mark.allow_network` marker for per-test overrides
- New CLI option: `--test-categories-enforcement=strict|warn|off`
- `HermeticityViolationError` exception hierarchy for resource violations
- `NetworkAccessViolationError` with detailed remediation guidance
- `NetworkBlockerPort` interface following hexagonal architecture
- `EnforcementMode` enum for configuration
- Comprehensive documentation:
  - User guide: `docs/user-guide/network-isolation.md`
  - Troubleshooting: `docs/troubleshooting/network-violations.md`
  - Examples: `docs/examples/network-isolation.md`
  - ADR: `docs/architecture/adr-001-network-isolation.md`

### Changed
- Test size restrictions now include network access rules (see documentation)

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
