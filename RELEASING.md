# Release Guide

This document provides comprehensive instructions for releasing new versions of pytest-test-categories.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Release Process](#release-process)
- [Version Numbering](#version-numbering)
- [Changelog Guidelines](#changelog-guidelines)
- [TestPyPI Validation](#testpypi-validation)
- [Troubleshooting](#troubleshooting)
- [Rollback Procedure](#rollback-procedure)
- [Security Notes](#security-notes)

## Overview

pytest-test-categories uses **automated releases** via GitHub Actions with **PyPI Trusted Publishers** (OIDC authentication). The release workflow is triggered when a git tag matching `v*.*.*` is pushed.

### Automated Release Pipeline

```
Tag Push (v*.*.*)
    |
    v
+-------------------+
| Validate Version  |  Ensures tag matches pyproject.toml version
+-------------------+
    |
    v
+-------------------+
| Build Package     |  Creates wheel and sdist, generates attestations
+-------------------+
    |
    v
+-------------------+
| Test Installation |  Verifies package installs on all platforms
| (9 combinations)  |  (Ubuntu/macOS/Windows x Python 3.11/3.12/3.13)
+-------------------+
    |
    v
+-------------------+
| GitHub Release    |  Creates release with changelog notes and artifacts
+-------------------+
    |
    v
+-------------------+
| Publish to PyPI   |  Uses Trusted Publishers (OIDC) for secure publishing
+-------------------+
    |
    v
+-------------------+
| Verify Release    |  Installs from PyPI to confirm availability
+-------------------+
```

## Prerequisites

Before creating a release, ensure:

1. **All CI checks pass** on the main branch
2. **Changelog is updated** with the new version's changes
3. **Version is bumped** in `pyproject.toml`
4. **Documentation is current** (README, docs/, CLAUDE.md)
5. **No blocking issues** are open for this release

### Required Permissions

- Write access to the repository
- Ability to create tags and releases

### Infrastructure Requirements

The following must be configured (already set up for this project):

- **PyPI Trusted Publisher**: OIDC authentication configured at pypi.org
- **TestPyPI Trusted Publisher**: OIDC authentication configured at test.pypi.org
- **GitHub Environments**: `pypi` and `testpypi` environments configured

## Release Process

### Step 1: Prepare the Release

1. **Create a release branch** (optional but recommended for significant releases):

   ```bash
   git checkout main
   git pull origin main
   git checkout -b release/vX.Y.Z
   ```

2. **Bump the version** in `pyproject.toml`:

   ```bash
   # Edit pyproject.toml and update the version line
   # version = "X.Y.Z"
   ```

   Alternatively, use commitizen for automated version bumping:

   ```bash
   uv run cz bump --dry-run  # Preview what will happen
   uv run cz bump            # Bump version and update CHANGELOG.md
   ```

3. **Update CHANGELOG.md** following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format:

   ```markdown
   ## [X.Y.Z] - YYYY-MM-DD

   ### Added
   - New feature descriptions

   ### Changed
   - Modifications to existing features

   ### Fixed
   - Bug fixes

   ### Deprecated
   - Features being phased out

   ### Removed
   - Features that were removed

   ### Security
   - Security-related fixes
   ```

4. **Commit the version bump**:

   ```bash
   git add pyproject.toml CHANGELOG.md
   git commit -m "chore: release version X.Y.Z"
   ```

5. **Create a pull request** for the release (if using a release branch):

   ```bash
   git push origin release/vX.Y.Z
   # Create PR via GitHub UI or gh CLI
   gh pr create --title "Release vX.Y.Z" --body "Release version X.Y.Z"
   ```

6. **Merge the PR** after review and CI passes.

### Step 2: Validate on TestPyPI (Recommended)

Before publishing to production PyPI, validate the release on TestPyPI:

1. **Trigger the TestPyPI workflow**:

   - Go to: [Actions > Release](https://github.com/mikelane/pytest-test-categories/actions/workflows/release.yml)
   - Click "Run workflow"
   - Check "Publish to TestPyPI (for validation before release)"
   - Click "Run workflow"

2. **Wait for the workflow to complete** and verify success.

3. **Test installation from TestPyPI**:

   ```bash
   pip install --index-url https://test.pypi.org/simple/ \
     --extra-index-url https://pypi.org/simple/ \
     pytest-test-categories==X.Y.Z
   ```

   Note: `--extra-index-url` is needed because TestPyPI may not have all dependencies.

4. **Verify the installed package**:

   ```bash
   python -c "import pytest_test_categories; print(pytest_test_categories.__version__)"
   pytest --co -q  # Verify plugin loads
   ```

### Step 3: Create the Release

1. **Create and push the git tag**:

   ```bash
   git checkout main
   git pull origin main
   VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
   git tag -a "v$VERSION" -m "Release v$VERSION"
   git push origin "v$VERSION"
   ```

2. **The release workflow triggers automatically** when the tag is pushed.

3. **Monitor the workflow**:

   - Go to: [Actions](https://github.com/mikelane/pytest-test-categories/actions)
   - Watch the "Release" workflow progress through all stages

### Step 4: Monitor Publishing

The workflow performs these steps automatically:

1. **Validate Version**: Ensures tag matches `pyproject.toml` version
2. **Build Distribution**: Creates wheel and sdist with build attestations
3. **Test Installation**: Verifies package installs on all supported platforms
4. **Create GitHub Release**: Publishes release with changelog notes and artifacts
5. **Publish to PyPI**: Uses Trusted Publishers for secure, tokenless publishing
6. **Verify Publication**: Installs from PyPI to confirm availability

### Step 5: Verify the Release

1. **Check the GitHub Release**:

   - Go to: [Releases](https://github.com/mikelane/pytest-test-categories/releases)
   - Verify the release notes and attached artifacts

2. **Check PyPI**:

   - Go to: https://pypi.org/project/pytest-test-categories/
   - Verify the new version is listed

3. **Test installation**:

   ```bash
   pip install --upgrade pytest-test-categories
   python -c "import pytest_test_categories; print(pytest_test_categories.__version__)"
   ```

4. **Verify the deployment summary** in the workflow run for links and status.

## Version Numbering

This project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html):

```
MAJOR.MINOR.PATCH
```

- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality in a backwards-compatible manner
- **PATCH**: Backwards-compatible bug fixes

### Pre-release Versions

For pre-release versions, use suffixes:

- `X.Y.Z-alpha.N` - Early testing, unstable
- `X.Y.Z-beta.N` - Feature complete, testing
- `X.Y.Z-rc.N` - Release candidate, final testing

### Development Status

The project is currently in **Beta** (`Development Status :: 4 - Beta`). This means:

- API may change between minor versions
- Production use is supported but monitor for updates
- Breaking changes will be documented in CHANGELOG.md

## Changelog Guidelines

The CHANGELOG.md follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.

### Categories

Use these categories in order:

1. **Added** - New features
2. **Changed** - Changes to existing functionality
3. **Deprecated** - Features to be removed in future versions
4. **Removed** - Features removed in this version
5. **Fixed** - Bug fixes
6. **Security** - Security-related fixes

### Best Practices

- Write for users, not developers
- Link to issues/PRs where appropriate: `(#123)`
- Be specific about what changed and why
- Include migration instructions for breaking changes
- Group related changes together

### Example Entry

```markdown
## [0.4.0] - 2025-01-15

### Added
- Network isolation enforcement for small tests (#69)
  - New `--test-categories-enforcement` CLI option
  - Blocks network access when enforcement is `strict` or `warn`
- `NetworkBlockerPort` interface following hexagonal architecture (#74)

### Changed
- Small tests now have network access blocked when enforcement is enabled
- Improved error messages for timing violations

### Fixed
- Timer state machine now properly handles edge cases (#78)
```

## TestPyPI Validation

### When to Use TestPyPI

- Before any production release
- When testing packaging changes
- When updating build configuration
- After significant dependency changes

### TestPyPI Workflow

1. **Trigger manual workflow** with TestPyPI option enabled
2. **Install from TestPyPI**:

   ```bash
   pip install --index-url https://test.pypi.org/simple/ \
     --extra-index-url https://pypi.org/simple/ \
     pytest-test-categories==X.Y.Z
   ```

3. **Run validation tests**:

   ```bash
   # Verify import
   python -c "import pytest_test_categories; print(pytest_test_categories.__version__)"

   # Verify plugin registration
   pytest --co -q

   # Run a simple test
   pytest --help | grep test-categories
   ```

### TestPyPI Limitations

- Packages may be deleted periodically
- Not all dependencies may be available
- Use `--extra-index-url https://pypi.org/simple/` for missing dependencies
- Version numbers cannot be reused (even after deletion)

## Troubleshooting

### Version Mismatch Error

**Symptom**: "Tag version does not match package version"

**Cause**: The git tag version doesn't match `pyproject.toml` version.

**Solution**:

```bash
# Check current version
grep '^version = ' pyproject.toml

# Delete incorrect tag (if not yet published)
git tag -d vX.Y.Z
git push origin :refs/tags/vX.Y.Z

# Create correct tag
VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
git tag -a "v$VERSION" -m "Release v$VERSION"
git push origin "v$VERSION"
```

### Authentication Failure

**Symptom**: "403 Forbidden" or "Authentication failed" during PyPI publish

**Cause**: Trusted Publisher not configured correctly.

**Solution**:

1. Verify Trusted Publisher configuration at pypi.org:
   - Go to: https://pypi.org/manage/project/pytest-test-categories/settings/publishing/
   - Ensure GitHub repository and workflow are correctly configured

2. Check the workflow file name matches the Trusted Publisher configuration

3. Verify the `environment` in the workflow matches the Trusted Publisher

### Package Already Exists

**Symptom**: "File already exists" error

**Cause**: Version already published to PyPI (versions cannot be overwritten).

**Solution**:

- Bump the version number (even for a patch fix)
- Update CHANGELOG.md with the new version
- Create a new tag and release

### TestPyPI Issues

**Symptom**: Package not found or dependency errors on TestPyPI

**Solutions**:

1. Wait a few minutes for index to update
2. Use `--extra-index-url https://pypi.org/simple/` for dependencies
3. Check TestPyPI directly: https://test.pypi.org/project/pytest-test-categories/

### Build Attestation Failures

**Symptom**: "Error generating attestation" during build

**Cause**: Missing `id-token: write` permission or attestation service issue.

**Solution**:

1. Verify workflow has `id-token: write` permission
2. Check GitHub's attestation service status
3. Attestation failure is non-blocking; release can proceed

### Installation Test Failures

**Symptom**: Package installs on some platforms but not others

**Cause**: Platform-specific code or missing dependencies.

**Solution**:

1. Review the failing platform's logs
2. Check for hardcoded paths or OS-specific code
3. Verify all dependencies are available for all platforms
4. Test locally on the failing platform if possible

## Rollback Procedure

If a release has critical issues after publication:

### Option 1: Yank the Release (Recommended)

Yanking hides the release from default installation but keeps it available for pinned versions.

1. **Yank on PyPI**:

   - Go to: https://pypi.org/manage/project/pytest-test-categories/releases/
   - Find the problematic version
   - Click "Options" > "Yank release"
   - Provide a reason (e.g., "Critical bug in feature X, use vX.Y.Z+1 instead")

2. **Update GitHub Release**:

   - Edit the release on GitHub
   - Add a warning to the release notes
   - Consider marking as pre-release

3. **Create a patch release**:

   ```bash
   # Fix the issue
   git checkout -b hotfix/critical-fix
   # Make fixes...
   git commit -m "fix: critical issue description"

   # Bump patch version
   # Edit pyproject.toml: version = "X.Y.Z+1"
   git add pyproject.toml CHANGELOG.md
   git commit -m "chore: release version X.Y.Z+1"

   # Merge and release
   git checkout main
   git merge hotfix/critical-fix
   git push origin main

   # Create new release tag
   git tag -a "vX.Y.Z+1" -m "Release vX.Y.Z+1 (hotfix)"
   git push origin "vX.Y.Z+1"
   ```

### Option 2: Delete the Release (PyPI Does Not Support This)

PyPI does not allow deleting releases. You can only:

- Yank releases (hides from default installation)
- Delete files (but not versions)

### Communication

After a rollback:

1. **Post a GitHub issue** explaining the problem and fix
2. **Update release notes** with warnings and recommended version
3. **Notify users** through appropriate channels
4. **Update documentation** if the issue affects usage

## Security Notes

### Trusted Publishers (OIDC)

This project uses **PyPI Trusted Publishers** for secure, tokenless authentication:

- No API tokens stored in GitHub Secrets
- Authentication based on GitHub's OIDC identity
- Scoped to specific workflows and environments
- Automatic token rotation (no manual secret management)

### How It Works

1. GitHub Actions requests an OIDC token from GitHub's identity provider
2. The token contains claims about the workflow, repository, and environment
3. PyPI verifies the token against the configured Trusted Publisher
4. If verified, PyPI grants temporary upload credentials

### Configuration

Trusted Publisher is configured at:

- **PyPI**: https://pypi.org/manage/project/pytest-test-categories/settings/publishing/
- **TestPyPI**: https://test.pypi.org/manage/project/pytest-test-categories/settings/publishing/

Settings:

- **Owner**: `mikelane`
- **Repository**: `pytest-test-categories`
- **Workflow**: `release.yml`
- **Environment**: `pypi` or `testpypi`

### Security Best Practices

1. **Use environments** with protection rules for production releases
2. **Review workflow changes** carefully (they affect publishing permissions)
3. **Monitor release activity** in GitHub Actions logs
4. **Keep dependencies updated** to avoid supply chain attacks
5. **Verify build attestations** on published packages

### Build Attestations

Each release generates **build attestations** that can be verified:

```bash
# Verify attestation for a release
gh attestation verify pytest_test_categories-X.Y.Z-py3-none-any.whl \
  --owner mikelane
```

Attestations provide:

- Proof of which workflow built the package
- Cryptographic verification of build provenance
- Protection against tampering

## Additional Resources

- [PyPI Trusted Publishers Documentation](https://docs.pypi.org/trusted-publishers/)
- [GitHub Actions OIDC](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
- [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
- [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
- [Python Packaging User Guide](https://packaging.python.org/)
- [Build Attestations](https://docs.github.com/en/actions/security-guides/using-artifact-attestations-to-establish-provenance-for-builds)
