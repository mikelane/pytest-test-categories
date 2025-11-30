# Design Philosophy

This document explains the core design philosophy behind pytest-test-categories and the reasoning for its strict enforcement approach.

## The "No Escape Hatches" Philosophy

pytest-test-categories is built on a fundamental principle: **small tests must be truly hermetic**. This means:

- No network access (not even localhost for small tests)
- No filesystem access (except pytest's `tmp_path`)
- No subprocess spawning
- No database connections (including in-memory SQLite)
- No sleep calls
- Must complete within 1 second

Unlike many testing tools that provide optional enforcement or easy overrides, pytest-test-categories is intentionally strict. This design choice is rooted in Google's "Software Engineering at Google" testing philosophy.

### Why Strictness Matters

**1. Flaky tests are expensive**

Flaky tests erode trust in the test suite. When developers can't rely on test results, they:
- Ignore legitimate failures
- Re-run tests multiple times "just in case"
- Spend hours debugging phantom failures
- Eventually stop writing tests altogether

By enforcing hermeticity at the plugin level, we eliminate entire categories of flakiness.

**2. Escape hatches become the norm**

When a tool provides easy ways to bypass restrictions, teams inevitably use them:

```python
# "Just this once" becomes standard practice
@pytest.mark.small
@pytest.mark.allow_network  # Hypothetical escape hatch
def test_user_service():
    response = requests.get("http://api.example.com/users")  # Still flaky!
    ...
```

pytest-test-categories deliberately does not provide such markers. If your test needs network access, it should be marked as `@pytest.mark.medium` or larger.

**3. Categories have meaning**

The test size categories are not arbitrary labels - they define contracts:

| Category | Meaning | Resources |
|----------|---------|-----------|
| Small | Unit test, single process, in-memory | None (hermetic) |
| Medium | Integration test, single machine | Localhost network, filesystem |
| Large | System test, multi-machine possible | Full network, external services |
| XLarge | Performance/stress test | Unlimited |

If a "small" test can access the network, it's not really a small test. The label loses meaning.

## Trade-offs and Design Decisions

### Decision: Block all network for small tests

**What we chose**: Small tests cannot make any network connections, not even to localhost.

**Alternative considered**: Allow localhost connections for small tests.

**Rationale**: Even localhost connections can be flaky:
- Port conflicts in parallel test execution
- Service startup timing issues
- Resource exhaustion under load

If you need localhost, use `@pytest.mark.medium`. Medium tests allow localhost-only connections.

### Decision: Block in-memory SQLite

**What we chose**: Even `:memory:` SQLite databases are blocked in small tests.

**Alternative considered**: Allow in-memory databases since they don't involve I/O.

**Rationale**:
1. Consistency - database usage is database usage, regardless of storage
2. Design smell - if you need a database, your test might be too integrated
3. Encourages better patterns - use repository fakes, not in-memory databases

```python
# Instead of this:
@pytest.mark.small
def test_user_repository():
    conn = sqlite3.connect(":memory:")  # Blocked!
    repo = UserRepository(conn)
    ...

# Do this:
@pytest.mark.small
def test_user_repository():
    repo = FakeUserRepository()  # In-memory, no database
    ...
```

### Decision: Enforcement modes exist, but for migration only

**What we chose**: Three enforcement modes - `strict`, `warn`, and `off`.

**Why have modes if we're strict?**

The modes exist to support **gradual adoption**, not permanent bypass:

1. **off**: For initial exploration - see what would fail
2. **warn**: For migration - fix violations incrementally
3. **strict**: The destination - where you should end up

```toml
# pyproject.toml - a migration journey

# Week 1: Discovery
[tool.pytest.ini_options]
test_categories_enforcement = "off"

# Week 2-4: Migration
[tool.pytest.ini_options]
test_categories_enforcement = "warn"

# Week 5+: Enforced
[tool.pytest.ini_options]
test_categories_enforcement = "strict"
```

### Decision: No per-test exemptions

**What we chose**: No `@pytest.mark.allow_network` or similar markers.

**Alternative considered**: Per-test overrides like pytest-socket provides.

**Rationale**: Per-test overrides defeat the purpose:
- They proliferate (every test becomes "special")
- They're never removed (technical debt)
- They make the category meaningless

Instead, use the right category:

```python
# Wrong: Forcing a square peg into a round hole
@pytest.mark.small
@pytest.mark.allow_network  # DON'T DO THIS
def test_external_api():
    ...

# Right: Use the appropriate category
@pytest.mark.medium  # Honest about what the test does
def test_external_api():
    ...
```

## Comparison with Other Approaches

### pytest-socket

pytest-socket blocks network access and provides allowlisting:

```python
@pytest.mark.enable_socket
def test_with_network():
    ...
```

**Difference**: pytest-test-categories ties network blocking to test size categories. You don't opt in or out of blocking - you declare what kind of test you're writing.

### pyfakefs

pyfakefs provides a fake filesystem for testing:

```python
def test_file_operations(fs):
    fs.create_file("/path/to/file.txt")
    ...
```

**Difference**: pyfakefs replaces the filesystem with an in-memory fake. pytest-test-categories blocks access entirely for small tests. Both approaches work; they solve different problems:
- pyfakefs: "I need to test file operations"
- pytest-test-categories: "I need to enforce that small tests don't do file I/O"

### freezegun/time-machine

These tools freeze or control time:

```python
@freeze_time("2024-01-01")
def test_time_dependent():
    ...
```

**Difference**: Time-freezing is about testing time-dependent logic. pytest-test-categories' sleep blocking is about preventing arbitrary delays:

```python
# This is fine - testing time logic
@pytest.mark.small
@freeze_time("2024-01-01")
def test_date_formatting():
    assert format_date(datetime.now()) == "January 1, 2024"

# This is blocked - arbitrary delay
@pytest.mark.small
def test_polling():
    time.sleep(0.1)  # Blocked! Use proper synchronization
    check_state()
```

## The Distribution Target Philosophy

pytest-test-categories enforces not just individual test behavior but also the overall test distribution:

- **80% small tests** (hermetic, fast, reliable)
- **15% medium tests** (integration, localhost allowed)
- **5% large/xlarge tests** (system tests, full access)

### Why enforce distribution?

**The Testing Pyramid**: Teams naturally drift toward larger tests because they're "easier" to write:
- No need for mocks or fakes
- Can test "the real thing"
- Less upfront design

But larger tests are slower and less reliable. Enforcing distribution keeps teams honest.

**Economics**: If 80% of tests run in under 1 second each, your test suite stays fast even as it grows. If most tests are large, CI becomes a bottleneck.

### Tolerance bands

The targets have tolerance bands to be practical:
- Small: 80% (+/-5%) = 75-85%
- Medium: 15% (+/-5%) = 10-20%
- Large/XLarge: 5% (+/-3%) = 2-8%

These allow normal variation while preventing drift.

## Actionable Error Messages

When pytest-test-categories blocks something, it tells you exactly how to fix it:

```
============================================================
HermeticityViolationError
============================================================
Test: test_fetch_user_profile (tests/test_users.py:42)
Category: SMALL
Violation: Network access attempted

Details:
  Attempted connection to: api.example.com:443

Small tests have restricted resource access. Options:
  1. Mock the network call using responses, httpretty, or respx
  2. Use dependency injection to provide a fake HTTP client
  3. Change test category to @pytest.mark.medium (if network is required)

Documentation: https://pytest-test-categories.readthedocs.io/
============================================================
```

This philosophy of **helpful errors** is intentional:
1. Don't just say "no" - explain why
2. Provide multiple solutions - one might fit better
3. Link to documentation - for deeper learning

## Summary

pytest-test-categories is opinionated by design. It embodies the belief that:

1. **Test reliability is non-negotiable** - flaky tests destroy developer trust
2. **Categories should mean something** - a small test is hermetic or it's not small
3. **Strictness enables speed** - hermetic tests can run in parallel, always
4. **Gradual adoption, then enforcement** - modes are for migration, not bypass
5. **Help, don't just block** - every error should include remediation guidance

This philosophy produces test suites that are fast, reliable, and meaningful.
