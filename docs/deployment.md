# Deployment Guide

This document describes the CI/CD infrastructure for pytest-test-categories.

For step-by-step release instructions, see [RELEASING.md](../RELEASING.md).

## Table of Contents

- [Overview](#overview)
- [CI/CD Architecture](#cicd-architecture)
- [GitHub Configuration](#github-configuration)
- [Security](#security)
- [Troubleshooting](#troubleshooting)

## Overview

The project uses GitHub Actions for continuous integration and continuous deployment:

- **CI Pipeline**: Runs on every PR and push to main - tests, linting, security scanning
- **CD Pipeline**: Automated publishing to PyPI on GitHub releases
- **Security**: Daily scans, dependency updates, secret detection
- **Automation**: Dependabot for dependencies, auto-merge for safe updates

## CI/CD Architecture

### CI Workflow (`.github/workflows/ci.yml`)

**Triggers**: Push to main, pull requests, manual dispatch

**Jobs**:

1. **Test Matrix** (9 combinations)
   - OS: Ubuntu, macOS, Windows
   - Python: 3.11, 3.12, 3.13
   - Runs full test suite with coverage
   - Validates 100% coverage requirement
   - Uploads coverage to Codecov (Ubuntu + Python 3.12 only)

2. **Lint and Format Check**
   - Import sorting validation (isort)
   - Code formatting check (ruff format)
   - Linting (ruff check)

3. **Pre-commit Hooks**
   - Runs all pre-commit hooks in CI
   - Ensures local hooks match CI validation

4. **Build Package**
   - Creates wheel and source distribution
   - Validates package metadata
   - Uploads artifacts for inspection

5. **All Checks Pass**
   - Gate job ensuring all required checks pass
   - Used as branch protection requirement

**Performance Optimizations**:
- Dependency caching by OS and Python version
- Concurrent job execution where possible
- `fail-fast: false` to see all failures
- 10-minute timeout prevents hung tests

### CD Workflow (`.github/workflows/cd.yml`)

**Triggers**: GitHub release published, manual dispatch

**Jobs**:

1. **Validate Version**
   - Extracts version from `pyproject.toml`
   - Ensures tag matches package version (format: `v{version}`)
   - Prevents accidental version mismatches

2. **Build Distribution**
   - Creates wheel and source distribution
   - Validates package metadata
   - Uploads artifacts with version tag

3. **Test Installation** (9 combinations)
   - OS: Ubuntu, macOS, Windows
   - Python: 3.11, 3.12, 3.13
   - Installs built wheel
   - Verifies plugin registration
   - Catches platform-specific installation issues

4. **Publish to TestPyPI** (manual dispatch only)
   - Test deployment to TestPyPI
   - Use for pre-release validation
   - Requires: `TEST_PYPI_API_TOKEN` secret

5. **Publish to PyPI** (release only)
   - Automated deployment on release
   - Uses trusted publishing (OIDC) or API token
   - Requires: `PYPI_API_TOKEN` secret
   - Environment: `pypi` (for protection rules)

6. **Post-publish Validation**
   - Waits 60s for PyPI index update
   - Installs from PyPI to verify availability
   - Creates deployment summary

### Security Workflow (`.github/workflows/security.yml`)

**Triggers**: Push to main, PRs, daily at 2 AM UTC, manual dispatch

**Jobs**:

1. **Dependency Security Scan**
   - Exports dependencies via uv
   - Runs Safety check on production and dev dependencies
   - Generates security report artifact

2. **CodeQL Analysis**
   - GitHub's semantic code analysis
   - Runs security-extended and quality queries
   - Integrates with Security tab

3. **Dependency Review** (PR only)
   - Reviews new dependencies in PRs
   - Fails on moderate+ severity vulnerabilities
   - Blocks GPL-3.0, AGPL-3.0 licenses
   - Posts summary comment in PR

4. **Secret Scanning**
   - TruffleHog OSS for secret detection
   - Scans commit history
   - Only verified secrets fail the check

5. **OpenSSF Scorecard** (scheduled/manual only)
   - Security best practices scorecard
   - Uploads results to Security tab
   - Runs weekly to track improvements

### Dependency Automation

**Dependabot** (`.github/dependabot.yml`):
- Weekly dependency updates on Mondays at 3 AM
- Python dependencies and GitHub Actions
- Maximum 5 open PRs per ecosystem
- Auto-assigned to repository owner

**Auto-merge** (`.github/workflows/auto-merge.yml`):
- Automatically approves and merges patch/minor Dependabot updates
- Requires all CI checks to pass
- Comments on major updates for manual review
- Reduces maintenance burden for safe updates

## GitHub Configuration

### Required Secrets

Set these in **Settings → Secrets and variables → Actions**:

1. **`PYPI_API_TOKEN`** (required for releases)
   - Create at: https://pypi.org/manage/account/token/
   - Scope: Project-specific token for `pytest-test-categories`
   - Used by: CD workflow for PyPI publishing

2. **`TEST_PYPI_API_TOKEN`** (optional, for testing)
   - Create at: https://test.pypi.org/manage/account/token/
   - Scope: Project-specific token
   - Used by: Manual workflow dispatch to TestPyPI

3. **`CODECOV_TOKEN`** (optional, recommended)
   - Create at: https://codecov.io/
   - Used by: CI workflow for coverage reporting
   - Not required but provides better coverage tracking

### Branch Protection Rules

Configure in **Settings → Branches → Branch protection rules** for `main`:

**Basic Requirements**:
- ✅ Require a pull request before merging
  - ✅ Require approvals: 1
  - ✅ Dismiss stale pull request approvals when new commits are pushed
  - ✅ Require review from Code Owners

**Status Checks**:
- ✅ Require status checks to pass before merging
  - ✅ Require branches to be up to date before merging
  - **Required status checks**:
    - `All CI checks pass`
    - `Dependency Review`
    - `Secret Scanning`
    - `CodeQL Analysis`

**Additional Protections**:
- ✅ Require conversation resolution before merging
- ✅ Require linear history (optional, recommended)
- ✅ Do not allow bypassing the above settings

**Merge Options**:
- ✅ Allow squash merging
- ✅ Allow auto-merge
- ✅ Automatically delete head branches

### Environments

Create environments in **Settings → Environments**:

1. **`pypi`** (for production releases)
   - **Deployment protection rules**:
     - Required reviewers: Repository owner
     - Wait timer: 5 minutes (optional, allows abort)
   - **Environment secrets**: None (uses repo-level `PYPI_API_TOKEN`)

2. **`testpypi`** (for testing)
   - No protection rules needed
   - Used for manual testing before production

### Code Owners

Create `.github/CODEOWNERS`:

```
# Default owners for everything
* @mikelane

# CI/CD infrastructure requires SRE review
/.github/workflows/ @mikelane
/docs/DEPLOYMENT.md @mikelane

# Package configuration
/pyproject.toml @mikelane
/uv.lock @mikelane
```

### Security Settings

Configure in **Settings → Code security and analysis**:

- ✅ Dependency graph
- ✅ Dependabot alerts
- ✅ Dependabot security updates
- ✅ Grouped security updates
- ✅ Secret scanning
- ✅ Push protection for secret scanning

## Security

### Dependency Management

**Automated Updates**:
- Dependabot opens PRs weekly for dependency updates
- Auto-merge handles patch/minor updates automatically
- Major updates require manual review

**Security Scanning**:
- Daily security scans at 2 AM UTC
- Safety checks all dependencies for CVEs
- CodeQL analyzes code for security issues
- Dependency Review blocks vulnerable dependencies in PRs

**Manual Security Audit**:

```bash
# Export dependencies with uv
uv export --format requirements-txt > requirements.txt

# Run Safety
pip install safety
safety check --file requirements.txt --json

# Check for outdated packages
uv run pip list --outdated
```

### Secret Management

**GitHub Secrets**:
- Never commit secrets to repository
- Use GitHub Secrets for API tokens
- Rotate secrets periodically (every 6-12 months)

**Secret Scanning**:
- Automatic secret detection on push
- TruffleHog scans commit history
- Push protection prevents accidental commits

### SBOM (Software Bill of Materials)

Generate SBOM for supply chain security:

```bash
# Export dependencies with uv
uv export --format requirements-txt > requirements.txt

# Generate SBOM
pip install cyclonedx-bom
cyclonedx-py --requirements requirements.txt --output sbom.json

# Or use pip-audit
pip install pip-audit
pip-audit --format cyclonedx-json
```

## Troubleshooting

### CI Failures

**Tests Fail in CI but Pass Locally**:

1. Check Python version matrix - might be version-specific
2. Review dependency cache - clear cache by updating `uv.lock`
3. Check for timing-sensitive tests or race conditions
4. Ensure dependencies are synced correctly with `uv sync --all-groups`

**Coverage Validation Fails**:

1. Check `coverage_target.txt` value (should be 100.0)
2. Run locally: `uv run pytest && uv run python tests/_utils/check_coverage.py`
3. Review coverage report for missing lines
4. Update tests to achieve 100% coverage

**Pre-commit Hooks Fail**:

```bash
# Run pre-commit locally
uv run pre-commit run --all-files

# Update pre-commit hooks
uv run pre-commit autoupdate
```

### CD Failures

**Version Validation Fails**:

- Error: Tag version doesn't match package version
- Solution: Ensure tag format is `v{version}` matching `pyproject.toml`

```bash
# Check version
grep '^version = ' pyproject.toml | grep -oP '"\K[^"]+'

# Create correct tag
VERSION=$(grep '^version = ' pyproject.toml | grep -oP '"\K[^"]+')
git tag -a "v$VERSION" -m "Release v$VERSION"
```

**PyPI Publishing Fails**:

1. **Authentication Error**:
   - Verify `PYPI_API_TOKEN` secret is set correctly
   - Ensure token scope includes `pytest-test-categories` project
   - Check token hasn't expired

2. **Version Already Exists**:
   - PyPI doesn't allow overwriting versions
   - Bump version and create new release
   - Cannot delete versions from PyPI (can only yank)

3. **Package Validation Error**:
   - Validate package structure and metadata in `pyproject.toml`
   - Ensure all required classifiers are present
   - Validate README renders correctly on PyPI

**Installation Test Fails**:

- Platform-specific issue (Windows, macOS, Linux)
- Check for hardcoded paths or OS-specific code
- Review test output in specific OS job

### Security Scan Failures

**Safety Check Finds Vulnerability**:

1. Review the CVE details in the safety report
2. Check if update is available: `uv lock --upgrade-package {package}`
3. If no fix available, assess risk and consider alternatives
4. Document decision in security advisory if accepting risk

**CodeQL Alerts**:

1. Review alert in Security tab
2. Understand the potential vulnerability
3. Fix the code pattern causing the alert
4. Rerun CodeQL workflow to verify fix

**Secret Detected**:

1. **Immediately rotate the exposed secret**
2. Review git history to confirm exposure
3. Update GitHub secret with new value
4. Consider using `git filter-repo` to remove from history if needed

## Monitoring and Observability

See [monitoring](monitoring.md) for production observability recommendations.

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [uv Documentation](https://github.com/astral-sh/uv)
- [PyPI Publishing Guide](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)
- [OpenSSF Best Practices](https://bestpractices.coreinfrastructure.org/)
- [Python Security Considerations](https://docs.python.org/3/library/security_warnings.html)
