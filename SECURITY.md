# Security Policy

## Supported Versions

We take security seriously and actively maintain the following versions:

| Version | Supported          | End of Support |
| ------- | ------------------ | -------------- |
| 0.3.x   | :white_check_mark: | Current        |
| 0.2.x   | :x:                | Ended          |
| < 0.2   | :x:                | Ended          |

**Recommendation**: Always use the latest stable version to ensure you have the latest security patches.

## Security Update Policy

- **Critical vulnerabilities**: Patched within 24-48 hours
- **High severity**: Patched within 7 days
- **Medium severity**: Patched in next scheduled release
- **Low severity**: Addressed in regular maintenance

## Reporting a Vulnerability

We appreciate responsible disclosure of security vulnerabilities. **Please do not open public issues for security vulnerabilities.**

### How to Report

1. **Email**: Send details to [mikelane@gmail.com](mailto:mikelane@gmail.com) with subject line: **[SECURITY] pytest-test-categories vulnerability**

2. **Include**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)
   - Your contact information

3. **Encryption** (optional): If you prefer encrypted communication, request our PGP key

### What to Expect

**Within 24 hours**:
- Acknowledgment of your report
- Initial assessment of severity
- Timeline for investigation

**Within 7 days**:
- Detailed analysis of the vulnerability
- Confirmation or clarification needed
- Proposed fix timeline

**Before public disclosure**:
- We'll work with you to understand and fix the issue
- We'll coordinate disclosure timing
- We'll credit you in the security advisory (unless you prefer to remain anonymous)

## Security Best Practices for Users

### Installation

```bash
# Always verify package integrity
pip install pytest-test-categories --require-hashes

# Or use poetry with lock file
poetry install  # Uses poetry.lock for reproducible builds
```

### Configuration

- **Review pytest configuration**: Ensure test categorization doesn't execute untrusted code
- **Validate custom categories**: If using custom categories (future feature), validate configuration
- **Limit time thresholds**: Extremely high time limits could be used for DoS

### CI/CD Security

- **Pin dependencies**: Use exact versions in CI to prevent supply chain attacks
- **Review dependency updates**: Don't blindly accept dependency updates
- **Use minimal permissions**: GitHub Actions should use minimal necessary permissions

## Known Security Considerations

### Not Security Features

This plugin is designed for test organization and timing, **not** for:
- **Sandboxing tests**: Tests can still access system resources
- **Preventing malicious code**: Tests can execute arbitrary Python
- **Resource isolation**: Tests share the same Python process

### Security Boundaries

- **Pytest trust model**: We inherit pytest's trust model - tests are trusted code
- **No privilege escalation**: Plugin does not require or provide elevated permissions
- **File system access**: Plugin has same file system access as pytest

### Dependencies

We maintain minimal dependencies to reduce attack surface:
- `pytest` - Core testing framework (trusted)
- `pydantic` - Data validation (widely used, actively maintained)
- `beartype` - Runtime type checking (minimal dependencies)
- `icontract` - Design by contract (pure Python)

All dependencies are:
- Actively maintained
- Have strong security track records
- Regularly updated via Dependabot

## Security Scanning

### Automated Scanning

We use:
- **Dependabot**: Automatic dependency vulnerability scanning
- **GitHub Security Advisories**: Monitoring for known vulnerabilities
- **CodeQL** (future): Static analysis for security issues

### Manual Review

- **Code review**: All PRs reviewed for security implications
- **Security checklist**: Maintainers use security review checklist
- **Third-party audit**: Planned for v1.0 release

## Vulnerability Disclosure Timeline

### Private Disclosure Period

1. **Day 0**: Vulnerability reported privately
2. **Day 1**: Acknowledged and confirmed
3. **Day 7**: Fix developed and tested
4. **Day 14**: Patch released privately to security contacts
5. **Day 21**: Public disclosure and patch release

**Exception**: Critical vulnerabilities may be disclosed sooner if actively exploited

### Public Disclosure

When we publicly disclose:
- **GitHub Security Advisory**: Created with CVE (if applicable)
- **Release notes**: Security fix highlighted
- **CHANGELOG.md**: Security fix documented
- **Communication**: Announced via GitHub Discussions and social media
- **Credit**: Reporter credited (with permission)

## Security Contacts

### Primary Contact

- **Name**: Mike Lane
- **Email**: [mikelane@gmail.com](mailto:mikelane@gmail.com)
- **Response Time**: Within 24 hours

### Security Team

As the project grows, we'll establish a dedicated security team. For now:
- All security reports go to primary contact
- Maintainers are notified on need-to-know basis
- Private security fork used for fixes

## Security Acknowledgments

We thank the following individuals for responsibly disclosing security issues:

*(None yet - be the first!)*

## Security-Related Configuration

### Recommended pytest Configuration

```toml
[tool.pytest.ini_options]
# Fail on first error to limit damage from malicious tests
addopts = ["-x"]

# Don't allow tests to modify pytest configuration
# (This is a general best practice, not specific to this plugin)
```

### CI/CD Recommendations

```yaml
# GitHub Actions
name: Security Checks

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5

      - name: Run Bandit security scan
        run: poetry run bandit -r src/

      - name: Check for known vulnerabilities
        run: poetry run safety check

      - name: Verify poetry.lock is up to date
        run: poetry lock --check
```

## Compliance

### License Compliance

- Dual licensed: CC BY-NC 4.0 and Commercial
- All dependencies are compatible licenses
- No GPL dependencies (to avoid license conflicts)

### Data Privacy

- **No telemetry**: Plugin does not collect or transmit usage data
- **No external requests**: Plugin does not make network requests
- **Local only**: All operations are local to the test environment

## Future Security Enhancements

### Planned for v1.0

- [ ] Security audit by third-party firm
- [ ] CodeQL static analysis in CI
- [ ] SBOM (Software Bill of Materials) generation
- [ ] Signed releases with GPG

### Under Consideration

- [ ] Bug bounty program
- [ ] Security advisory mailing list
- [ ] Automated security testing in CI
- [ ] Reproducible builds

## Questions?

Security questions that aren't vulnerabilities:
- **Discussions**: [GitHub Discussions](https://github.com/mikelane/pytest-test-categories/discussions)
- **General contact**: [mikelane@gmail.com](mailto:mikelane@gmail.com)

---

**Thank you for helping keep pytest-test-categories and our users safe!**

*Last updated: November 2024*
