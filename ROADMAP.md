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

## Current State (v0.6.0) - November 2025

### Completed Capabilities

- ✅ Four test size categories (small, medium, large, xlarge)
- ✅ Timing enforcement with fixed limits (1s/300s/900s)
- ✅ Distribution validation with target percentages (80/15/5)
- ✅ **Distribution enforcement modes** (off/warn/strict)
- ✅ Test size reporting (basic and detailed)
- ✅ Base test classes for easy categorization
- ✅ Comprehensive test coverage (100%)
- ✅ CI/CD pipeline with multi-version Python support (3.11, 3.12, 3.13, 3.14)
- ✅ Pre-commit hooks for quality enforcement
- ✅ Hexagonal architecture (Ports and Adapters pattern throughout)

### Resource Isolation (Phase 1 Complete)

- ✅ **Network Isolation** - Block all network access for small tests
- ✅ **Medium Network Restriction** - Localhost-only for medium tests
- ✅ **Process Isolation** - Block subprocess spawning in small tests
- ✅ **Database Isolation** - Block database connections in small tests
- ✅ **Thread Monitoring** - Warn when small tests use threading primitives
- ✅ **Enforcement modes** - `warn` (default) and `strict` modes

### Remaining for v1.0.0

- Filesystem isolation implementation (ADR + docs complete)
- Sleep blocking for small tests
- Configurable time limits
- JSON/XML report export

## Revised Timeline (Velocity-Based)

Based on development velocity with Claude Code assistance, the project is **~6 weeks ahead of schedule**.

### Phase 1: Resource Isolation (Q4 2025) ✅ COMPLETE
**Delivered: v0.4.0 - v0.6.0**

- ✅ Network access blocking for small tests
- ✅ Localhost-only restriction for medium tests
- ✅ Process/subprocess blocking for small tests
- ✅ Database connection blocking for small tests
- ✅ Thread monitoring with warnings
- ✅ Enforcement modes: `warn` (default) and `strict`
- ✅ Clear error messages with remediation guidance

### Phase 2: Configuration & Polish (December 2025)
**Target: v0.7.0 - v0.9.0**

**Scope:**
- User-configurable time limits via pytest configuration
- Sleep blocking for small tests
- Filesystem isolation implementation
- JSON/XML report export for CI integration
- Documentation overhaul with real-world examples

### Phase 3: v1.0 Stable Release (January 2026)
**Target: v1.0.0**

**Acceptance Criteria:**
- [x] Network isolation enforcement
- [x] Process isolation enforcement
- [x] Database isolation enforcement
- [x] Thread monitoring
- [x] Distribution enforcement modes
- [ ] Filesystem isolation enforcement
- [ ] Sleep blocking for small tests
- [ ] Configurable time limits and tolerances
- [ ] JSON/XML reporting
- [ ] Comprehensive documentation
- [ ] Zero known critical bugs
- [ ] Security audit completed
- [ ] Performance benchmarks published

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

### High Priority (v1.0 Requirements)

1. **Configurable Time Limits**
   - Allow users to override default limits
   - Support per-category configuration
   - Validate configuration at startup

2. **Sleep Blocking**
   - `time.sleep()` blocked for small tests
   - Warning/strict modes
   - Clear error messages

3. **Filesystem Isolation**
   - Block filesystem access for small tests (except temp dirs)
   - Configurable allowed paths
   - ADR-002 and documentation already complete

4. **Enhanced Reporting**
   - JSON export for CI integration
   - JUnit XML format with size metadata
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

### Milestone: v0.7.0 - Configuration & Reporting (Target: December 2025)

**Acceptance Criteria**:
- [ ] Configurable time limits via pyproject.toml/pytest.ini
- [ ] Sleep blocking for small tests
- [ ] JSON report export for CI integration
- [ ] Documentation updates

### Milestone: v0.8.0 - Filesystem Isolation (Target: December 2025)

**Acceptance Criteria**:
- [ ] Filesystem access blocked for small tests (except temp dirs)
- [ ] Configurable allowed paths
- [ ] Warning/strict modes
- [ ] Integration with existing enforcement infrastructure

### Milestone: v1.0.0 - Stable Release (Target: January 2026)

**Acceptance Criteria**:
- [ ] Full resource isolation (network, process, database, filesystem, sleep)
- [ ] Configurable time limits
- [ ] JSON/XML reporting
- [ ] Comprehensive documentation
- [ ] Zero critical bugs
- [ ] Security audit completed
- [ ] Performance benchmarks

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

*Last Updated: November 2025*
*Next Review: December 2025*
