# Reporting

pytest-test-categories provides detailed reporting on test sizes, timing, and distribution through terminal output and command-line options.

## Test Size Labels

By default, the plugin appends size labels to test node IDs during collection:

```
tests/test_validation.py::test_email_valid[SMALL]
tests/test_repository.py::test_create_user[MEDIUM]
tests/test_e2e.py::test_checkout_flow[LARGE]
```

This makes it easy to identify test sizes in pytest output.

## Distribution Summary

After test collection, a distribution summary is displayed:

```
======================== Test Size Distribution ========================
Small:   45 tests (81.8%) - Target: 80% +/- 5% [OK]
Medium:   8 tests (14.5%) - Target: 15% +/- 5% [OK]
Large:    2 tests ( 3.6%) - Target:  5% +/- 3% [OK]
XLarge:   0 tests ( 0.0%)
========================================================================
Total: 55 tests
```

## Test Size Report

Use the `--test-size-report` option for detailed reporting:

### Basic Report

```bash
pytest --test-size-report=basic
```

Output:

```
===================== Test Size Report (Basic) =====================
SMALL:   45 tests,  0.82s total,  0.018s avg
MEDIUM:   8 tests, 12.34s total,  1.543s avg
LARGE:    2 tests, 45.67s total, 22.835s avg
XLARGE:   0 tests,  0.00s total,  0.000s avg
====================================================================
Total:   55 tests, 58.83s total
```

### Detailed Report

```bash
pytest --test-size-report=detailed
```

Output:

```
===================== Test Size Report (Detailed) =====================
SMALL Tests (45 tests, 0.82 seconds total):
  test_validation.py::test_email_valid              PASSED   0.001s
  test_validation.py::test_email_invalid            PASSED   0.001s
  test_parser.py::test_parse_json                   PASSED   0.003s
  test_parser.py::test_parse_xml                    PASSED   0.004s
  test_calculator.py::test_add                      PASSED   0.001s
  ... (40 more)

MEDIUM Tests (8 tests, 12.34 seconds total):
  test_repository.py::test_create_user              PASSED   1.234s
  test_repository.py::test_update_user              PASSED   1.456s
  test_repository.py::test_delete_user              PASSED   1.123s
  test_cache.py::test_cache_hit                     PASSED   0.567s
  test_cache.py::test_cache_miss                    PASSED   0.789s
  test_cache.py::test_cache_expiration              PASSED   2.345s
  test_db_migration.py::test_migrate_up             PASSED   2.456s
  test_db_migration.py::test_migrate_down           PASSED   2.789s

LARGE Tests (2 tests, 45.67 seconds total):
  test_e2e.py::test_checkout_flow                   PASSED  23.456s
  test_e2e.py::test_signup_flow                     PASSED  22.214s

XLARGE Tests (0 tests):
  (none)

========================================================================
Total: 55 tests, 58.83 seconds
Passed: 55, Failed: 0, Skipped: 0
========================================================================
```

## Timing Violation Reports

When tests exceed their time limits, detailed violation information is provided:

```
FAILED test_slow.py::test_takes_too_long[SMALL]
E   TimingViolationError: Test exceeded time limit
E
E   Test: test_takes_too_long
E   Size: SMALL
E   Duration: 2.34 seconds
E   Limit: 1.00 second
E
E   Options:
E     1. Optimize the test to run faster
E     2. Change test category to @pytest.mark.medium
E     3. Split into smaller, focused tests
```

## Warning Messages

The plugin emits warnings for common issues:

### Missing Size Marker

```
PytestWarning: Test 'test_something' has no size marker.
Consider adding @pytest.mark.small, @pytest.mark.medium,
@pytest.mark.large, or @pytest.mark.xlarge.
```

### Distribution Warning

```
PytestWarning: Test distribution outside target range.
Small tests: 65% (target: 80% +/- 5%)
Consider converting medium/large tests to small tests.
```

## Terminal Summary

At the end of the test run, a summary is displayed:

```
========================= Test Categories Summary =========================
Distribution:
  Small:  45/55 (81.8%) [OK]
  Medium:  8/55 (14.5%) [OK]
  Large:   2/55 ( 3.6%) [OK]
  XLarge:  0/55 ( 0.0%)

Timing:
  Violations: 0
  Slowest test: test_e2e.py::test_checkout_flow (23.456s)

Warnings: 1
  - 1 test missing size marker
===========================================================================
```

### JSON Report

```bash
pytest --test-size-report=json
```

JSON output is printed to stdout. To save to a file:

```bash
pytest --test-size-report=json --test-size-report-file=report.json
```

Output:

```json
{
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:45.123456Z",
  "summary": {
    "total_tests": 55,
    "distribution": {
      "small": {"count": 45, "percentage": 81.8},
      "medium": {"count": 8, "percentage": 14.5},
      "large": {"count": 2, "percentage": 3.6},
      "xlarge": {"count": 0, "percentage": 0.0}
    },
    "violations": {
      "timing": 0,
      "hermeticity": {
        "network": 0,
        "filesystem": 0,
        "process": 0,
        "database": 0,
        "sleep": 0,
        "total": 0
      }
    }
  },
  "tests": [
    {
      "name": "test_validation.py::test_email_valid",
      "size": "small",
      "duration": 0.001,
      "status": "passed",
      "violations": []
    },
    {
      "name": "test_network.py::test_with_network_call",
      "size": "small",
      "duration": 0.234,
      "status": "passed",
      "violations": ["hermeticity:network"]
    }
  ]
}
```

#### JSON Schema

The JSON report includes:

- **version**: Schema version (currently "1.0.0")
- **timestamp**: ISO 8601 formatted UTC timestamp
- **summary**: Aggregate statistics
  - **total_tests**: Total number of tests
  - **distribution**: Count and percentage by test size
  - **violations**: Violation counts
    - **timing**: Number of tests exceeding time limits
    - **hermeticity**: Counts by violation type (network, filesystem, process, database, sleep, and total)
- **tests**: Array of test entries with name, size, duration, status, and violations

#### Hermeticity Violations

When running with `--test-categories-enforcement=warn`, the JSON report tracks hermeticity violations:

| Violation Type | Format in JSON | Description |
|---------------|----------------|-------------|
| Network | `hermeticity:network` | Blocked network connections |
| Filesystem | `hermeticity:filesystem` | Blocked filesystem access |
| Process | `hermeticity:process` | Blocked subprocess spawning |
| Database | `hermeticity:database` | Blocked database connections |
| Sleep | `hermeticity:sleep` | Blocked sleep calls |

Example with violations:

```bash
pytest --test-size-report=json --test-categories-enforcement=warn --test-size-report-file=report.json
```

```json
{
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:45.123456Z",
  "summary": {
    "total_tests": 3,
    "distribution": {
      "small": {"count": 3, "percentage": 100.0},
      "medium": {"count": 0, "percentage": 0.0},
      "large": {"count": 0, "percentage": 0.0},
      "xlarge": {"count": 0, "percentage": 0.0}
    },
    "violations": {
      "timing": 1,
      "hermeticity": {
        "network": 1,
        "filesystem": 0,
        "process": 0,
        "database": 2,
        "sleep": 0,
        "total": 3
      }
    }
  },
  "tests": [
    {
      "name": "test_slow.py::test_takes_too_long",
      "size": "small",
      "duration": 2.34,
      "status": "passed",
      "violations": ["timing"]
    },
    {
      "name": "test_api.py::test_external_call",
      "size": "small",
      "duration": 0.01,
      "status": "passed",
      "violations": ["hermeticity:network"]
    },
    {
      "name": "test_db.py::test_multiple_db_calls",
      "size": "small",
      "duration": 0.05,
      "status": "passed",
      "violations": ["hermeticity:database", "hermeticity:database"]
    }
  ]
}
```

## Customizing Output

### Verbose Mode

Use pytest's `-v` flag for more detailed output:

```bash
pytest -v --test-size-report=basic
```

### Quiet Mode

Use pytest's `-q` flag for minimal output:

```bash
pytest -q
```

Only failures and the final summary are shown.

### Color Output

The plugin respects pytest's color settings:

```bash
pytest --color=yes   # Force colors
pytest --color=no    # Disable colors
pytest --color=auto  # Auto-detect (default)
```

## Integration with CI/CD

### JUnit XML

Use pytest's JUnit XML output for CI integration:

```bash
pytest --junitxml=test-results.xml --test-size-report=basic
```

### Coverage Integration

Combine with coverage reporting:

```bash
pytest --cov=myapp --cov-report=xml --test-size-report=basic
```

### GitHub Actions Example

```yaml
- name: Run tests with size report
  run: |
    pytest \
      --test-size-report=detailed \
      --junitxml=test-results.xml \
      --cov=myapp \
      --cov-report=xml

- name: Upload test results
  uses: actions/upload-artifact@v4
  with:
    name: test-results
    path: test-results.xml
```
