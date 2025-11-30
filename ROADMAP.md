# pytest-test-categories Roadmap

This document outlines the vision, goals, and planned milestones for pytest-test-categories.

## Vision (2-3 Years)

**Become the de facto standard for test categorization, timing enforcement, and resource isolation in the Python ecosystem**, enabling teams to maintain fast, reliable, hermetic test suites that follow Google's "Software Engineering at Google" best practices.

### Strategic Position

pytest-test-categories is the **foundational component** of a commercial Python testing ecosystem:

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  pytest-test-       │     │  pytest-test-       │     │  [mutation          │
│  categories         │     │  impact             │     │  testing tool]      │
│                     │     │                     │     │                     │
│  "Which tests are   │     │  "Which tests cover │     │  "Are my tests      │
│   fast/hermetic?"   │     │   this code?"       │     │   catching bugs?"   │
│                     │     │                     │     │                     │
└─────────┬───────────┘     └──────────┬──────────┘     └──────────┬──────────┘
          │                            │                           │
          └────────────────┬───────────┴───────────────────────────┘
                           │
                           ▼
                 ┌─────────────────────┐
                 │      dioxide        │
                 │  "How do I write    │
                 │   testable code?"   │
                 └─────────────────────┘
```

**The killer integration:**
```bash
# Mutation test using only fast, hermetic tests that cover the changed code
pytest --mutate --impacted-by-diff origin/main -m small
```

This integration provides 10x faster mutation testing by combining:
- **Test size filtering** (pytest-test-categories): Only run fast tests
- **Impact analysis** (pytest-test-impact): Only run tests that cover mutated code
- **Hermeticity enforcement** (pytest-test-categories): Ensure reliable, non-flaky results

### Strategic Goals

1. **Foundation**: Be the cornerstone of the commercial Python testing ecosystem
2. **Hermeticity**: Enforce resource isolation so small tests are truly hermetic
3. **Best Practices**: Promote Google's test size philosophy across the Python community
4. **Integration**: Enable seamless integration with pytest-test-impact and mutation testing
5. **Performance**: Zero-overhead test categorization and timing
6. **Extensibility**: Pluggable architecture for custom categories and resource policies

## Current State (v0.7.0) - November 2025

### Completed Capabilities

- ✅ Four test size categories (small, medium, large, xlarge)
- ✅ Timing enforcement with configurable limits (default: 1s/300s/900s/900s)
- ✅ Distribution validation with target percentages (80/15/5)
- ✅ **Distribution enforcement modes** (off/warn/strict)
- ✅ Test size reporting (basic, detailed, and JSON)
- ✅ Base test classes for easy categorization
- ✅ Comprehensive test coverage (100%)
- ✅ CI/CD pipeline with multi-version Python support (3.11, 3.12, 3.13, 3.14)
- ✅ Pre-commit hooks for quality enforcement
- ✅ Hexagonal architecture (Ports and Adapters pattern throughout)

### Resource Isolation - COMPLETE

All resource isolation features are **fully implemented** and production-ready:

- ✅ **Network Isolation** - Block all network access for small tests, localhost-only for medium
- ✅ **Filesystem Isolation** - Block filesystem access for small tests (except tmp_path, tempdir)
- ✅ **Process Isolation** - Block subprocess spawning in small tests
- ✅ **Database Isolation** - Block database connections in small tests (including in-memory SQLite)
- ✅ **Sleep Blocking** - Block time.sleep() and asyncio.sleep() in small tests
- ✅ **Thread Monitoring** - Warn when small tests use threading primitives
- ✅ **External Systems Detection** - Warn when medium tests use testcontainers/docker
- ✅ **Enforcement modes** - `off` (default), `warn`, and `strict` modes
- ✅ **Configurable allowed paths** - `--test-categories-allowed-paths` CLI option

### Design Philosophy: No Override Markers

This plugin intentionally provides **NO per-test override markers** (e.g., `@pytest.mark.allow_network`).
This is a deliberate architectural decision, not a missing feature.

**Rationale:**
- Small tests must be hermetic. Period. No escape hatches.
- If a test needs external resources, it should be `@pytest.mark.medium`, not a small test with an exception.
- Override markers would undermine the entire philosophy and make enforcement meaningless.
- The correct remediation is always to either mock the dependency or upgrade the test category.

See each ADR in `docs/architecture/` for detailed rationale per resource type.

### Remaining for v1.0.0

- ✅ ~~Filesystem isolation implementation~~ DONE
- ✅ ~~Sleep blocking for small tests~~ DONE
- ✅ ~~Configurable time limits~~ DONE
- ✅ ~~JSON report export~~ DONE
- Comprehensive documentation review
- Final testing and polish

## Revised Timeline (Velocity-Based)

Based on development velocity with Claude Code assistance, the project is **~6 weeks ahead of schedule**.

### Phase 1: Resource Isolation (Q4 2025) ✅ COMPLETE
**Delivered: v0.4.0 - v0.7.0**

- ✅ Network access blocking for small tests
- ✅ Localhost-only restriction for medium tests
- ✅ Process/subprocess blocking for small tests
- ✅ Database connection blocking for small tests
- ✅ Filesystem isolation for small tests
- ✅ Sleep blocking for small tests
- ✅ Thread monitoring with warnings
- ✅ External systems detection for medium tests
- ✅ Enforcement modes: `off` (default), `warn`, and `strict`
- ✅ Clear error messages with remediation guidance
- ✅ Configurable time limits via CLI and ini options
- ✅ JSON report export

### Phase 2: Documentation & Polish (November-December 2025) ✅ COMPLETE
**Delivered: v0.7.0**

- ✅ Comprehensive user guide documentation
- ✅ Architecture documentation with ADRs
- ✅ Migration guide and common patterns
- ✅ API reference documentation
- ✅ Ecosystem integration guides
- ✅ Real-world example test suite
- ✅ Performance benchmarks
- ✅ Security audit

### Phase 3: v1.0 Stable Release (January 2026)
**Target: v1.0.0**

**Acceptance Criteria:**
- [x] Network isolation enforcement
- [x] Process isolation enforcement
- [x] Database isolation enforcement
- [x] Filesystem isolation enforcement
- [x] Sleep blocking for small tests
- [x] Thread monitoring
- [x] Distribution enforcement modes
- [x] Configurable time limits and tolerances
- [x] JSON reporting
- [x] Comprehensive documentation
- [ ] Zero known critical bugs (final verification)
- [x] Security audit completed
- [x] Performance benchmarks published

### Phase 4: Ecosystem Integration (Q1-Q2 2026)
**Target: v1.1.0 - v1.3.0**

**Scope:**
- Integration with pytest-test-impact
- pytest-xdist parallel execution support
- Dashboard integrations (Allure, ReportPortal)
- Historical trend tracking

### Phase 5: Advanced Features (Q3 2026+)
**Target: v2.0.0**

**Scope:**
- Custom test categories
- dioxide DI integration (automatic faking for small tests)
- ML-based test categorization suggestions
- Flaky test detection

## Feature Backlog

### Completed (v0.7.0)

1. ✅ **Configurable Time Limits**
   - Allow users to override default limits
   - Support per-category configuration via CLI and ini
   - Validate configuration at startup

2. ✅ **Sleep Blocking**
   - `time.sleep()` and `asyncio.sleep()` blocked for small tests
   - Warning/strict modes
   - Clear error messages with remediation

3. ✅ **Filesystem Isolation**
   - Block filesystem access for small tests (except temp dirs)
   - Configurable allowed paths via `--test-categories-allowed-paths`
   - Full implementation matching ADR-002

4. ✅ **Enhanced Reporting**
   - JSON export for CI integration via `--test-size-report=json`
   - Hermeticity violation reports

### Medium Priority (v1.x)

5. **pytest-test-impact Integration**
   - Size metadata API for impact queries
   - Combined filtering examples
   - CI optimization patterns

6. **Parallel Execution Support**
   - Full pytest-xdist compatibility
   - Per-worker timer isolation
   - Correct distribution validation

7. **Dashboard Integration**
   - Allure integration
   - ReportPortal integration
   - Historical trend tracking

### Low Priority (v2.0+)

8. **Custom Test Categories**
   - User-defined categories
   - Custom resource policies
   - Category inheritance

9. **dioxide Integration**
   - Automatic test double injection
   - Profile-based configuration
   - Premium feature tier

10. **Advanced Analytics**
    - ML-based categorization suggestions
    - Flaky test detection
    - Optimization recommendations

## Milestones

### Milestone: v0.7.0 - Complete Resource Isolation ✅ DELIVERED

**Acceptance Criteria** (ALL COMPLETE):
- [x] Configurable time limits via pyproject.toml/pytest.ini
- [x] Sleep blocking for small tests
- [x] Filesystem isolation for small tests
- [x] JSON report export for CI integration
- [x] Comprehensive documentation
- [x] All ADRs updated to "Implemented" status

### Milestone: v1.0.0 - Stable Release (Target: January 2026)

**Acceptance Criteria**:
- [x] Full resource isolation (network, process, database, filesystem, sleep)
- [x] Configurable time limits
- [x] JSON reporting
- [x] Comprehensive documentation
- [ ] Final testing and bug verification
- [x] Security audit completed
- [x] Performance benchmarks

**Note**: All v1.0.0 features are implemented. Release is pending final testing and polish.

### Milestone: v1.1.0 - Impact Integration (Target: Q1 2026)

**Acceptance Criteria**:
- [ ] Size metadata API for pytest-test-impact
- [ ] Combined filtering documentation
- [ ] CI optimization examples
- [ ] Integration test suite

### Milestone: v2.0.0 - Advanced Features (Target: Q3 2026)

**Acceptance Criteria**:
- [ ] Custom test categories
- [ ] dioxide integration (optional)
- [ ] ML-based suggestions
- [ ] Flaky test detection

## Success Metrics

### Project Health

- **Code Quality**: 100% test coverage maintained
- **Security**: Zero unpatched vulnerabilities
- **Performance**: < 1% overhead on test execution
- **Documentation**: 100% of public API documented

### Ecosystem Health

- **Integration**: Seamless with pytest-test-impact
- **Adoption**: Used by mutation testing tool users
- **Reliability**: Zero flaky tests in hermeticity-enforced suites

### Community Health

- **Contributors**: Growing contributor base
- **Issues**: < 7 day median response time
- **PRs**: < 14 day median merge time
- **Releases**: Monthly patches, quarterly minors

## Versioning Strategy

Following [Semantic Versioning 2.0.0](https://semver.org/):

- **MAJOR** (e.g., 1.0.0 → 2.0.0): Breaking changes to public API
- **MINOR** (e.g., 1.0.0 → 1.1.0): New features, backward compatible
- **PATCH** (e.g., 1.0.0 → 1.0.1): Bug fixes, backward compatible

### Release Cadence

- **Patch releases**: As needed for bug fixes (1-2 weeks)
- **Minor releases**: Quarterly for new features
- **Major releases**: Annually or when breaking changes required

## Contributing to the Roadmap

This roadmap is a living document that evolves based on:

- **Ecosystem Needs**: Integration requirements with pytest-test-impact and mutation testing
- **Community Feedback**: Your needs and priorities
- **Industry Trends**: Emerging best practices
- **Technical Capabilities**: New technologies and approaches

### How to Influence the Roadmap

1. **Share Your Use Case**: Open a discussion describing how you use pytest-test-categories
2. **Propose Features**: Use the feature request template
3. **Vote on Issues**: React with 👍 to issues you care about
4. **Contribute**: Submit PRs for features you want to see
5. **Provide Feedback**: Comment on proposed features

---

*Last Updated: November 30, 2025*
*Next Review: January 2026 (v1.0.0 Release)*
