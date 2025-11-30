# CI Integration Guide

This guide provides complete, copy-paste ready CI configuration examples for using pytest-test-categories in various CI/CD platforms.

## Core Principles

When integrating pytest-test-categories with CI:

1. **Run small tests first** - Get fast feedback (< 2 minutes)
2. **Run tests in parallel** - Small and medium tests can run concurrently
3. **Gate large tests** - Only run on main branch or before release
4. **Generate reports** - Track test distribution over time
5. **Enforce strictly** - Use `--test-categories-enforcement=strict`

## GitHub Actions

### Basic Workflow

A minimal workflow that runs all tests with size enforcement:

```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          pip install uv
          uv sync --all-groups

      - name: Run tests with enforcement
        run: |
          uv run pytest \
            --test-categories-enforcement=strict \
            --test-size-report=detailed \
            -v
```

### Complete Multi-Stage Workflow

A production-ready workflow with parallel test execution:

```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  UV_CACHE_DIR: /tmp/.uv-cache

jobs:
  # ===========================================================================
  # Small Tests: Fast feedback (runs first, < 2 minutes)
  # ===========================================================================
  small-tests:
    name: Small Tests (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.11", "3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
          cache-dependency-glob: "uv.lock"

      - name: Set up Python ${{ matrix.python-version }}
        run: uv python install ${{ matrix.python-version }}

      - name: Install dependencies
        run: uv sync --all-groups

      - name: Run small tests
        run: |
          uv run pytest -m small \
            --test-categories-enforcement=strict \
            --test-size-report=json \
            --test-size-report-file=small-tests-report.json \
            -v

      - name: Upload test report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: small-tests-report-py${{ matrix.python-version }}
          path: small-tests-report.json

  # ===========================================================================
  # Medium Tests: Container-based tests (runs in parallel with small)
  # ===========================================================================
  medium-tests:
    name: Medium Tests
    runs-on: ubuntu-latest
    # No needs: - runs in parallel with small-tests

    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
          cache-dependency-glob: "uv.lock"

      - name: Set up Python
        run: uv python install 3.12

      - name: Install dependencies
        run: uv sync --all-groups

      - name: Run medium tests
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test
        run: |
          uv run pytest -m medium \
            --test-categories-enforcement=strict \
            --test-size-report=json \
            --test-size-report-file=medium-tests-report.json \
            -v

      - name: Upload test report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: medium-tests-report
          path: medium-tests-report.json

  # ===========================================================================
  # Large Tests: Full integration (only on main branch)
  # ===========================================================================
  large-tests:
    name: Large Tests
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    needs: [small-tests, medium-tests]

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
          cache-dependency-glob: "uv.lock"

      - name: Set up Python
        run: uv python install 3.12

      - name: Install dependencies
        run: uv sync --all-groups

      - name: Run large tests
        run: |
          uv run pytest -m large \
            --test-categories-enforcement=strict \
            --test-size-report=json \
            --test-size-report-file=large-tests-report.json \
            -v

      - name: Upload test report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: large-tests-report
          path: large-tests-report.json

  # ===========================================================================
  # Coverage: Combined coverage from all test sizes
  # ===========================================================================
  coverage:
    name: Coverage Report
    runs-on: ubuntu-latest
    needs: [small-tests, medium-tests]

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
          cache-dependency-glob: "uv.lock"

      - name: Set up Python
        run: uv python install 3.12

      - name: Install dependencies
        run: uv sync --all-groups

      - name: Run all tests with coverage
        run: |
          uv run coverage run -m pytest \
            --test-categories-enforcement=warn \
            --test-size-report=detailed
          uv run coverage report --show-missing
          uv run coverage xml

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: coverage.xml
          fail_ci_if_error: false

  # ===========================================================================
  # Distribution Check: Validate 80/15/5 distribution
  # ===========================================================================
  distribution-check:
    name: Check Test Distribution
    runs-on: ubuntu-latest
    needs: [small-tests]

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
          cache-dependency-glob: "uv.lock"

      - name: Set up Python
        run: uv python install 3.12

      - name: Install dependencies
        run: uv sync --all-groups

      - name: Check distribution
        run: |
          uv run pytest --collect-only \
            --test-categories-distribution-enforcement=warn \
            -q
```

### PR-Only Small Tests

Skip slow tests on pull requests:

```yaml
# .github/workflows/pr-tests.yml
name: PR Tests

on:
  pull_request:
    branches: [main]

jobs:
  quick-tests:
    name: Quick Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -e .[test]

      - name: Run small tests only
        run: |
          pytest -m small \
            --test-categories-enforcement=strict \
            -v
```

## GitLab CI

### Basic Configuration

```yaml
# .gitlab-ci.yml
stages:
  - test
  - coverage

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip/

# Small tests - run first and fast
small-tests:
  stage: test
  image: python:3.12-slim
  script:
    - pip install uv
    - uv sync --all-groups
    - uv run pytest -m small --test-categories-enforcement=strict -v
  artifacts:
    reports:
      junit: junit.xml
    paths:
      - small-tests-report.json
    when: always

# Medium tests - run in parallel with small
medium-tests:
  stage: test
  image: python:3.12-slim
  services:
    - name: postgres:15-alpine
      alias: postgres
  variables:
    POSTGRES_USER: test
    POSTGRES_PASSWORD: test
    POSTGRES_DB: test
    DATABASE_URL: postgresql://test:test@postgres:5432/test
  script:
    - pip install uv
    - uv sync --all-groups
    - uv run pytest -m medium --test-categories-enforcement=strict -v
  artifacts:
    reports:
      junit: junit.xml
    paths:
      - medium-tests-report.json
    when: always

# Large tests - only on main branch
large-tests:
  stage: test
  image: python:3.12-slim
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
  script:
    - pip install uv
    - uv sync --all-groups
    - uv run pytest -m large --test-categories-enforcement=strict -v
  artifacts:
    reports:
      junit: junit.xml
    when: always

# Coverage report
coverage:
  stage: coverage
  image: python:3.12-slim
  needs: [small-tests, medium-tests]
  script:
    - pip install uv
    - uv sync --all-groups
    - uv run coverage run -m pytest --test-categories-enforcement=warn
    - uv run coverage report
    - uv run coverage xml
  coverage: '/TOTAL.*\s+(\d+%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
```

### Complete GitLab Configuration

```yaml
# .gitlab-ci.yml
stages:
  - lint
  - test
  - coverage
  - deploy

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  key: "$CI_JOB_NAME"
  paths:
    - .cache/pip/
    - .venv/

.python-base:
  image: python:3.12-slim
  before_script:
    - pip install uv
    - uv sync --all-groups

# ===========================================================================
# Linting Stage
# ===========================================================================
lint:
  extends: .python-base
  stage: lint
  script:
    - uv run ruff check .
    - uv run ruff format --check .
    - uv run mypy src/

# ===========================================================================
# Test Stage
# ===========================================================================
small-tests:
  extends: .python-base
  stage: test
  parallel:
    matrix:
      - PYTHON_VERSION: ["3.11", "3.12", "3.13"]
  image: python:${PYTHON_VERSION}-slim
  script:
    - uv run pytest -m small \
        --test-categories-enforcement=strict \
        --test-size-report=json \
        --test-size-report-file=small-tests-report.json \
        --junitxml=junit-small.xml \
        -v
  artifacts:
    reports:
      junit: junit-small.xml
    paths:
      - small-tests-report.json
    when: always

medium-tests:
  extends: .python-base
  stage: test
  services:
    - name: postgres:15-alpine
      alias: postgres
    - name: redis:7-alpine
      alias: redis
  variables:
    POSTGRES_USER: test
    POSTGRES_PASSWORD: test
    POSTGRES_DB: test
    DATABASE_URL: postgresql://test:test@postgres:5432/test
    REDIS_URL: redis://redis:6379
  script:
    - uv run pytest -m medium \
        --test-categories-enforcement=strict \
        --test-size-report=json \
        --test-size-report-file=medium-tests-report.json \
        --junitxml=junit-medium.xml \
        -v
  artifacts:
    reports:
      junit: junit-medium.xml
    paths:
      - medium-tests-report.json
    when: always

large-tests:
  extends: .python-base
  stage: test
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
    - if: $CI_PIPELINE_SOURCE == "schedule"
  needs: [small-tests, medium-tests]
  script:
    - uv run pytest -m large \
        --test-categories-enforcement=strict \
        --test-size-report=json \
        --test-size-report-file=large-tests-report.json \
        --junitxml=junit-large.xml \
        -v
  artifacts:
    reports:
      junit: junit-large.xml
    paths:
      - large-tests-report.json
    when: always

# ===========================================================================
# Coverage Stage
# ===========================================================================
coverage:
  extends: .python-base
  stage: coverage
  needs: [small-tests, medium-tests]
  script:
    - uv run coverage run -m pytest \
        --test-categories-enforcement=warn \
        --test-size-report=detailed
    - uv run coverage report --show-missing
    - uv run coverage xml
    - uv run coverage html
  coverage: '/TOTAL.*\s+(\d+%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
    paths:
      - htmlcov/
    expire_in: 1 week
```

## Jenkins

### Declarative Pipeline

```groovy
// Jenkinsfile
pipeline {
    agent any

    environment {
        UV_CACHE_DIR = "${WORKSPACE}/.uv-cache"
    }

    stages {
        stage('Setup') {
            steps {
                sh 'pip install uv'
                sh 'uv sync --all-groups'
            }
        }

        stage('Small Tests') {
            steps {
                sh '''
                    uv run pytest -m small \
                        --test-categories-enforcement=strict \
                        --test-size-report=json \
                        --test-size-report-file=small-tests-report.json \
                        --junitxml=junit-small.xml \
                        -v
                '''
            }
            post {
                always {
                    junit 'junit-small.xml'
                    archiveArtifacts artifacts: 'small-tests-report.json'
                }
            }
        }

        stage('Medium Tests') {
            steps {
                sh '''
                    uv run pytest -m medium \
                        --test-categories-enforcement=strict \
                        --test-size-report=json \
                        --test-size-report-file=medium-tests-report.json \
                        --junitxml=junit-medium.xml \
                        -v
                '''
            }
            post {
                always {
                    junit 'junit-medium.xml'
                    archiveArtifacts artifacts: 'medium-tests-report.json'
                }
            }
        }

        stage('Large Tests') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                    uv run pytest -m large \
                        --test-categories-enforcement=strict \
                        --test-size-report=json \
                        --test-size-report-file=large-tests-report.json \
                        --junitxml=junit-large.xml \
                        -v
                '''
            }
            post {
                always {
                    junit 'junit-large.xml'
                    archiveArtifacts artifacts: 'large-tests-report.json'
                }
            }
        }

        stage('Coverage') {
            steps {
                sh '''
                    uv run coverage run -m pytest \
                        --test-categories-enforcement=warn \
                        --test-size-report=detailed
                    uv run coverage report --show-missing
                    uv run coverage xml
                    uv run coverage html
                '''
            }
            post {
                always {
                    publishHTML(target: [
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'htmlcov',
                        reportFiles: 'index.html',
                        reportName: 'Coverage Report'
                    ])
                    cobertura coberturaReportFile: 'coverage.xml'
                }
            }
        }
    }

    post {
        always {
            cleanWs()
        }
    }
}
```

### Parallel Execution Pipeline

```groovy
// Jenkinsfile
pipeline {
    agent none

    stages {
        stage('Test') {
            parallel {
                stage('Small Tests - Python 3.11') {
                    agent { docker { image 'python:3.11-slim' } }
                    steps {
                        sh 'pip install uv && uv sync --all-groups'
                        sh 'uv run pytest -m small --test-categories-enforcement=strict -v'
                    }
                }
                stage('Small Tests - Python 3.12') {
                    agent { docker { image 'python:3.12-slim' } }
                    steps {
                        sh 'pip install uv && uv sync --all-groups'
                        sh 'uv run pytest -m small --test-categories-enforcement=strict -v'
                    }
                }
                stage('Medium Tests') {
                    agent { docker { image 'python:3.12-slim' } }
                    steps {
                        sh 'pip install uv && uv sync --all-groups'
                        sh 'uv run pytest -m medium --test-categories-enforcement=strict -v'
                    }
                }
            }
        }

        stage('Large Tests') {
            when { branch 'main' }
            agent { docker { image 'python:3.12-slim' } }
            steps {
                sh 'pip install uv && uv sync --all-groups'
                sh 'uv run pytest -m large --test-categories-enforcement=strict -v'
            }
        }
    }
}
```

## Coverage Integration

### Codecov with pytest-test-categories

```yaml
# .github/workflows/coverage.yml
name: Coverage

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  coverage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          pip install uv
          uv sync --all-groups

      - name: Run tests with coverage
        run: |
          uv run coverage run -m pytest \
            --test-categories-enforcement=warn \
            --test-size-report=detailed
          uv run coverage xml

      - name: Upload to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: coverage.xml
          flags: unittests
          fail_ci_if_error: true
```

### Codecov Configuration

```yaml
# codecov.yml
coverage:
  precision: 2
  round: down
  range: "70...100"
  status:
    project:
      default:
        target: auto
        threshold: 1%
    patch:
      default:
        target: auto
        threshold: 1%

flags:
  unittests:
    paths:
      - src/
    carryforward: true
```

## Gradual Migration CI

For projects migrating to pytest-test-categories:

```yaml
# .github/workflows/migration.yml
name: Migration Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  # Warn mode for all tests - see violations but don't fail
  test-with-warnings:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -e .[test]

      - name: Run tests (warn mode)
        run: |
          pytest --test-categories-enforcement=warn \
            --test-size-report=detailed 2>&1 | tee test-output.txt

      - name: Check for violations
        run: |
          if grep -q "HermeticityViolation" test-output.txt; then
            echo "::warning::Hermeticity violations detected - see test output"
            grep "HermeticityViolation" test-output.txt
          fi

  # Strict mode for small tests only
  small-tests-strict:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -e .[test]

      - name: Run small tests (strict)
        run: |
          pytest -m small --test-categories-enforcement=strict -v
```

## Related Documentation

- [Migration Guide](migration-guide.md) - Step-by-step migration process
- [Common Patterns](common-patterns.md) - Fixture and mocking patterns
- [Sample Project Workflow](https://github.com/mikelane/pytest-test-categories/blob/main/examples/sample_project/.github/workflows/test.yml) - Complete working example
