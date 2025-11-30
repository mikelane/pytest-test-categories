# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


### BREAKING CHANGE

- The plugin now requires session-specific state management, which may affect existing configurations.

### Feat

- Extend filesystem isolation to block pathlib, os, and shutil operations (#120)
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

## v0.7.0 (2025-11-29)

### Feat

- Add sleep blocking for small tests (#118)
- Add configurable time limits for test size categories (#117)
- Add JSON report export for CI integration (#116)

### Fix

- **ci**: add Python 3.14 to release workflow test matrix

## v0.6.0 (2025-11-28)

### Fix

- **ci**: add shell: bash to Verify plugin registration step
- **release**: update __version__ to 0.6.0 in __init__.py
- recategorize pytester tests from small to medium (#99)

## v0.5.0 (2025-11-28)

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
