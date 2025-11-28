---
name: Release
about: Prepare a new version release
title: 'Release vX.Y.Z'
labels: release
---

## Release Version

**Version:** `X.Y.Z`

## Pre-Release Checklist

### Version and Changelog

- [ ] Version bumped in `pyproject.toml`
- [ ] CHANGELOG.md updated with all changes for this version
- [ ] Version follows [Semantic Versioning](https://semver.org/)
- [ ] Changelog follows [Keep a Changelog](https://keepachangelog.com/) format

### Code Quality

- [ ] All CI checks passing on main branch
- [ ] No blocking issues open for this release
- [ ] All planned features/fixes for this release are merged

### Documentation

- [ ] README.md is current
- [ ] API documentation is up to date
- [ ] Any new features are documented
- [ ] Migration guide included (if breaking changes)

### Testing

- [ ] Full test suite passes (`uv run pytest`)
- [ ] Tests pass on all supported Python versions (`uv run tox`)
- [ ] 100% code coverage maintained
- [ ] Manual testing of key features completed

### TestPyPI Validation (Recommended)

- [ ] TestPyPI workflow triggered and completed successfully
- [ ] Package installs correctly from TestPyPI
- [ ] Plugin loads and functions correctly

```bash
# Validation commands
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  pytest-test-categories==X.Y.Z

python -c "import pytest_test_categories; print(pytest_test_categories.__version__)"
pytest --co -q  # Verify plugin loads
```

## Release Notes Preview

<!-- Copy the CHANGELOG.md section for this version -->

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
-

### Changed
-

### Fixed
-
```

## Post-Merge Actions

After this PR is merged:

1. **Create and push the git tag:**
   ```bash
   git checkout main
   git pull origin main
   VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
   git tag -a "v$VERSION" -m "Release v$VERSION"
   git push origin "v$VERSION"
   ```

2. **Monitor the release workflow** at [Actions](https://github.com/mikelane/pytest-test-categories/actions)

3. **Verify the release:**
   - Check [GitHub Releases](https://github.com/mikelane/pytest-test-categories/releases)
   - Check [PyPI](https://pypi.org/project/pytest-test-categories/)
   - Test installation: `pip install --upgrade pytest-test-categories`

## Rollback Plan

If issues are discovered after release:

1. Yank the release on PyPI
2. Create a hotfix branch
3. Bump patch version and fix the issue
4. Create a new release

See [RELEASING.md](../RELEASING.md#rollback-procedure) for detailed rollback instructions.

## Additional Notes

<!-- Any additional context, known issues, or special instructions for this release -->
