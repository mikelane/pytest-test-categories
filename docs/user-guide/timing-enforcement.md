# Timing Enforcement

pytest-test-categories enforces time limits for each test size category. Tests that exceed their time limit will fail with a clear error message.

## Time Limits by Size

| Size | Time Limit |
|------|------------|
| Small | 1 second |
| Medium | 5 minutes (300 seconds) |
| Large | 15 minutes (900 seconds) |
| XLarge | 15 minutes (900 seconds) |

## How Timing Works

The plugin uses high-resolution wall-clock timing (`time.perf_counter()`) to measure test execution:

1. **Timer starts**: Before the test's call phase begins
2. **Test executes**: Your test code runs normally
3. **Timer stops**: After the test's call phase completes
4. **Validation**: Duration is compared against the test's size limit

Timing is measured for the "call" phase only, not setup or teardown fixtures.

## Timing Violations

When a test exceeds its time limit, a `TimingViolationError` is raised:

```
E   TimingViolationError: Test exceeded time limit
E
E   Test: test_slow_function
E   Size: SMALL
E   Duration: 2.34 seconds
E   Limit: 1.00 second
E
E   Options:
E     1. Optimize the test to run faster
E     2. Change test category to @pytest.mark.medium
E     3. Split into smaller, focused tests
```

## Best Practices

### Keep Small Tests Fast

Small tests should complete in well under 1 second. If a test is approaching the limit, consider:

1. **Mocking slow dependencies**: Replace I/O operations with mocks
2. **Reducing test data**: Use minimal data sets
3. **Focusing the test**: Test one thing per test

```python
import pytest

@pytest.mark.small
def test_user_creation_fast(mocker):
    """Fast test using mocks instead of real I/O."""
    # Mock the email sender
    mock_sender = mocker.patch("myapp.email.send_welcome_email")

    user = create_user("alice@example.com")

    assert user.email == "alice@example.com"
    mock_sender.assert_called_once()
```

### Choose Appropriate Sizes

If a test legitimately needs more time, use the appropriate size marker:

```python
@pytest.mark.medium  # 5 minutes allowed
def test_database_migration(test_database):
    """This test needs time for database operations."""
    migrator = DatabaseMigrator(test_database)
    migrator.run_all_migrations()
    assert migrator.current_version == LATEST_VERSION
```

### Avoid Time-Based Tests

Tests that use `time.sleep()` or wait for specific durations are often flaky. Instead:

```python
# Avoid this
@pytest.mark.small
def test_debounce():
    debouncer.trigger()
    time.sleep(0.5)  # Wastes time and may cause timing issues
    assert debouncer.was_called

# Do this instead
@pytest.mark.small
def test_debounce(fake_clock):
    debouncer = Debouncer(clock=fake_clock)
    debouncer.trigger()
    fake_clock.advance(0.5)  # Instant, deterministic
    assert debouncer.was_called
```

## Monitoring Test Duration

Use the test size report to identify slow tests:

```bash
pytest --test-size-report=detailed
```

This outputs individual test durations:

```
===================== Test Size Report (Detailed) =====================
SMALL Tests (45 tests, 0.82 seconds total):
  test_validation.py::test_email_valid              PASSED   0.001s
  test_validation.py::test_email_invalid            PASSED   0.001s
  test_parser.py::test_parse_json                   PASSED   0.003s
  ...

MEDIUM Tests (8 tests, 12.34 seconds total):
  test_repository.py::test_create_user              PASSED   1.234s
  test_repository.py::test_update_user              PASSED   1.456s
  ...
========================================================================
```

## Timer Architecture

The timing system uses hexagonal architecture for testability:

- **Port**: `TestTimer` abstract interface defines the timer contract
- **Production Adapter**: `WallTimer` uses `time.perf_counter()` for real timing
- **Test Adapter**: `FakeTimer` provides controllable time for testing

This design ensures:
- Unit tests are fast and deterministic
- Integration tests validate real timing behavior
- The timer logic can be tested without system clock dependencies

## Troubleshooting

### Test Intermittently Fails Timing

If a test sometimes exceeds the time limit:

1. Check for resource contention in parallel test runs
2. Look for garbage collection pauses
3. Consider if the test is doing too much
4. Review if the test size is appropriate

### Timer Doesn't Seem Accurate

The timer measures wall-clock time, which includes:
- Time spent in fixtures (setup/teardown is separate)
- Any I/O operations
- CPU scheduling delays

For the most accurate timing:
- Run tests in isolation: `pytest test_specific.py -x`
- Minimize background processes
- Use appropriate test sizes for the workload
