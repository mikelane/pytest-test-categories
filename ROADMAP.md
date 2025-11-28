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

## Current State (v0.3.0)

### Completed Capabilities

- ✅ Four test size categories (small, medium, large, xlarge)
- ✅ Timing enforcement with fixed limits (1s/300s/900s)
- ✅ Distribution validation with target percentages (80/15/5)
- ✅ Test size reporting (basic and detailed)
- ✅ Base test classes for easy categorization
- ✅ Comprehensive test coverage (100%)
- ✅ CI/CD pipeline with multi-version Python support (3.11, 3.12, 3.13, 3.14)
- ✅ Pre-commit hooks for quality enforcement
- ✅ Hexagonal architecture (WallTimer/FakeTimer adapters)

### Known Limitations

- No resource isolation enforcement (network, filesystem, sleep)
- Fixed time limits (not user-configurable)
- Limited reporting formats (terminal only)
- No integration with test impact analysis
- No parallel execution optimization
- No custom category support

## Revised Timeline (Velocity-Based)

Based on realistic development velocity (10-15 hours/week with Claude Code assistance):

### Phase 1: Resource Isolation (Q4 2025)
**Target: v0.4.0 - v0.6.0**

This is the **critical differentiator** that makes pytest-test-categories valuable for mutation testing integration.

**Scope:**
- Network access blocking for small tests
- Filesystem access blocking for small tests
- `time.sleep()` blocking for small tests
- Enforcement modes: `warn` (default) and `strict`
- Clear error messages with remediation guidance

**Why First:**
- Creates the "moat" around the commercial ecosystem
- Small tests must be hermetic for reliable mutation testing
- Enables the killer integration with pytest-test-impact

### Phase 2: Configuration & Polish (Q1 2026)
**Target: v0.7.0 - v0.9.0**

**Scope:**
- User-configurable time limits via pytest configuration
- Per-category configuration
- JSON/XML report export for CI integration
- Documentation overhaul with real-world examples
- Migration guides from v0.x

### Phase 3: v1.0 Stable Release (Late January 2026)
**Target: v1.0.0**

**Acceptance Criteria:**
- [ ] Resource isolation enforcement (network, filesystem, sleep)
- [ ] Configurable time limits and tolerances
- [ ] Comprehensive documentation
- [ ] Production deployment case studies
- [ ] Zero known critical bugs
- [ ] Security audit completed
- [ ] Performance benchmarks published

### Phase 4: Ecosystem Integration (Q2-Q3 2026)
**Target: v1.1.0 - v1.3.0**

**Scope:**
- Integration with pytest-test-impact
- pytest-xdist parallel execution support
- Dashboard integrations (Allure, ReportPortal)
- Historical trend tracking

### Phase 5: Advanced Features (Q4 2026+)
**Target: v2.0.0**

**Scope:**
- Custom test categories
- dioxide DI integration (automatic faking for small tests)
- ML-based test categorization suggestions
- Flaky test detection

## Resource Isolation Feature (Priority #1)

### The Problem

Small tests should be **hermetic** — producing the same result at 3am on Sunday or during peak traffic on Black Friday. Currently, pytest-test-categories only enforces timing; a "small" test can still:

- Make network requests (flaky, slow)
- Write to the filesystem (side effects, race conditions)
- Call `time.sleep()` (slow, timing-dependent)

### The Solution

**Enforcement mode** that blocks prohibited resources for small tests:

```toml
# pyproject.toml
[tool.pytest.ini_options]
test_categories_enforcement = "strict"  # or "warn" (default)

# small tests will FAIL if they:
# - Make network connections
# - Access filesystem outside allowed paths
# - Call time.sleep()
```

### Design Principles

1. **Enforcement over magic**: When a test fails because it accessed the network, the developer learns something. Silent fakes teach nothing.

2. **Gradual adoption**: `warn` mode lets teams see violations without breaking CI. `strict` mode enforces compliance.

3. **Clear errors**: Error messages explain WHY the resource is blocked and HOW to fix it (mock the dependency, use a test double, or change the test size).

4. **No hidden behavior**: Unlike automatic DI injection, enforcement is explicit and predictable.

### Implementation Approach

Using Python's import hooks and monkey-patching (similar to `gevent`):

```python
# Conceptual implementation
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    if is_small_test(item) and enforcement_enabled():
        with block_network(), block_filesystem(), block_sleep():
            yield
    else:
        yield
```

### Resource Blocking Strategies

| Resource | Strategy | Fallback |
|----------|----------|----------|
| Network | Patch `socket.socket` | Raise `HermeticityViolationError` |
| Filesystem | Patch `open`, `pathlib.Path` | Allow only temp dirs |
| Sleep | Patch `time.sleep` | Raise or warn |

### Future: dioxide Integration

After enforcement is mature, **optional** DI integration:

```python
# Future feature - NOT in v1.0
@pytest.mark.small  # dioxide auto-injects FakeHttpClient, FakeFileSystem
def test_user_creation(user_service: UserService):
    ...
```

This is a **premium feature** that depends on dioxide adoption.

## pytest-test-impact Integration

### The Value Proposition

When pytest-test-impact is available, pytest-test-categories enables:

```bash
# Run only small tests that cover changed code
pytest --impacted-by-diff origin/main -m small
```

### Integration Points

1. **Size-filtered impact queries**: "Which small tests cover this file?"
2. **Combined CI optimization**: Fast feedback on small tests, then medium/large
3. **Mutation testing acceleration**: Only run fast, relevant tests against mutations

### Implementation

pytest-test-impact will query pytest-test-categories for test size metadata:

```python
# pytest-test-impact queries test sizes
tests = impact_map.get_tests_for_line("src/auth/login.py", 42)
small_tests = [t for t in tests if categories.get_size(t) == TestSize.SMALL]
```

## Mutation Testing Integration

### The Killer Combo

```bash
pytest --mutate --impacted-by-diff origin/main -m small
```

This command:
1. Finds code changed from `origin/main`
2. Generates mutations for changed lines
3. Queries pytest-test-impact for tests covering those lines
4. Filters to only `@pytest.mark.small` tests (via pytest-test-categories)
5. Runs those tests against mutations
6. Reports mutation score

**Result**: Mutation testing in 2 minutes instead of 2 hours.

### Why This Matters

pytest-test-categories is the **moat** around the commercial mutation testing tool:

- Without test sizes: Must run all tests against all mutations (slow)
- With test sizes: Run only fast, hermetic tests (10x faster)
- With hermeticity enforcement: Results are reliable (no flakes)

## Feature Backlog

### High Priority (v1.0 Requirements)

1. **Resource Isolation Enforcement**
   - Network blocking for small tests
   - Filesystem blocking for small tests
   - Sleep blocking for small tests
   - `warn` and `strict` enforcement modes
   - Clear error messages with remediation

2. **Configurable Time Limits**
   - Allow users to override default limits
   - Support per-category configuration
   - Validate configuration at startup

3. **Enhanced Reporting**
   - JSON export for CI integration
   - JUnit XML format with size metadata
   - Hermeticity violation reports

4. **Documentation Improvements**
   - Resource isolation guide
   - Migration from v0.x guide
   - Real-world case studies
   - Integration guides

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

### Milestone: v0.4.0 - Network Isolation (Target: December 2025)

**Acceptance Criteria**:
- [ ] Network access blocked for small tests in strict mode
- [ ] Warning issued in warn mode
- [ ] Clear error message with remediation guidance
- [ ] Documentation for network isolation
- [ ] Tests for isolation behavior

### Milestone: v0.5.0 - Filesystem Isolation (Target: December 2025)

**Acceptance Criteria**:
- [ ] Filesystem access blocked for small tests (except temp dirs)
- [ ] Configurable allowed paths
- [ ] Warning/strict modes
- [ ] Documentation and examples

### Milestone: v0.6.0 - Sleep Blocking (Target: January 2026)

**Acceptance Criteria**:
- [ ] `time.sleep()` blocked for small tests
- [ ] Warning/strict modes
- [ ] Clear error messages
- [ ] Complete resource isolation suite

### Milestone: v1.0.0 - Stable Release (Target: Late January 2026)

**Acceptance Criteria**:
- [ ] Full resource isolation (network, filesystem, sleep)
- [ ] Configurable time limits
- [ ] JSON/XML reporting
- [ ] Comprehensive documentation
- [ ] Zero critical bugs
- [ ] Security audit completed
- [ ] Performance benchmarks

### Milestone: v1.1.0 - Impact Integration (Target: Q2 2026)

**Acceptance Criteria**:
- [ ] Size metadata API for pytest-test-impact
- [ ] Combined filtering documentation
- [ ] CI optimization examples
- [ ] Integration test suite

### Milestone: v2.0.0 - Advanced Features (Target: Q4 2026)

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
