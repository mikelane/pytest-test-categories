# Production Monitoring and Observability

This document provides recommendations for monitoring pytest-test-categories usage in production environments.

## Table of Contents

- [Overview](#overview)
- [Key Metrics](#key-metrics)
- [Observability Stack](#observability-stack)
- [Metrics Collection](#metrics-collection)
- [Alerting](#alerting)
- [Cost Optimization](#cost-optimization)
- [Example Implementations](#example-implementations)

## Overview

While pytest-test-categories is a development tool, monitoring its usage patterns provides valuable insights:

- Test suite health and evolution
- CI/CD pipeline performance
- Developer productivity metrics
- Quality gates effectiveness
- Resource utilization in CI

## Key Metrics

### Test Distribution Metrics

Track test size distribution over time to ensure healthy test pyramid:

```python
# Metric: test_size_distribution
# Labels: size (small, medium, large, xlarge), project, branch
# Type: Gauge
test_size_distribution{size="small", project="pytest-test-categories", branch="main"} 0.82
test_size_distribution{size="medium", project="pytest-test-categories", branch="main"} 0.15
test_size_distribution{size="large", project="pytest-test-categories", branch="main"} 0.03
```

**Why it matters**:
- Detects test pyramid degradation (too many large tests)
- Identifies teams/projects needing coaching on test sizing
- Tracks impact of test refactoring initiatives

**Alert on**:
- Small test percentage drops below 50% (critical)
- Large/XLarge percentage exceeds 10% (warning)
- Sudden shifts in distribution (>10% change week-over-week)

### Test Timing Metrics

Monitor test execution times to catch performance regressions:

```python
# Metric: test_duration_seconds
# Labels: size, test_name, project, outcome (passed, failed, skipped)
# Type: Histogram
test_duration_seconds_bucket{size="small", outcome="passed", le="0.5"} 245
test_duration_seconds_bucket{size="small", outcome="passed", le="1.0"} 298
test_duration_seconds_bucket{size="small", outcome="passed", le="+Inf"} 300

# Metric: test_timing_violations
# Labels: size, project
# Type: Counter
test_timing_violations_total{size="small", project="pytest-test-categories"} 5
```

**Why it matters**:
- Identifies slow tests before they violate timing constraints
- Tracks timing violation trends
- Helps prioritize performance optimization work

**Alert on**:
- Tests consistently near timing limits (>80% of limit)
- Timing violations increase week-over-week
- Individual test duration increases >20% compared to baseline

### CI Pipeline Metrics

Track CI performance impact of test suite:

```python
# Metric: ci_test_suite_duration_seconds
# Labels: project, branch, python_version, os
# Type: Histogram
ci_test_suite_duration_seconds{project="pytest-test-categories", branch="main", python_version="3.12"} 45.2

# Metric: ci_test_failures
# Labels: project, branch, failure_type (timing_violation, assertion, error)
# Type: Counter
ci_test_failures_total{project="pytest-test-categories", failure_type="timing_violation"} 12
```

**Why it matters**:
- CI duration directly impacts developer productivity
- Test failures indicate quality issues or flaky tests
- Resource costs in CI infrastructure

**Alert on**:
- CI test suite duration increases >30% compared to baseline
- Flaky test rate exceeds 1% (tests that fail intermittently)
- Timing violations block PRs consistently

### Coverage Metrics

Monitor test coverage trends:

```python
# Metric: test_coverage_percentage
# Labels: project, branch, module
# Type: Gauge
test_coverage_percentage{project="pytest-test-categories", branch="main"} 100.0

# Metric: uncovered_lines
# Labels: project, file
# Type: Gauge
uncovered_lines{project="pytest-test-categories", file="plugin.py"} 0
```

**Why it matters**:
- Coverage degradation indicates quality issues
- Identifies modules with poor coverage
- Validates quality gates are enforced

**Alert on**:
- Coverage drops below target (100% for this project)
- New PRs reduce coverage
- Coverage target validation failures in CI

## Observability Stack

Recommended open-source stack for cost-effective monitoring:

### Metrics Collection and Storage

**Prometheus** (self-hosted)
- Time-series database for metrics
- Efficient storage with configurable retention
- Pull-based model - scrapes exporters
- Cost: $0 (self-hosted on spot instances)

**Alternatives**:
- VictoriaMetrics (better compression, lower resource usage)
- Thanos (long-term storage for Prometheus)
- Cortex (multi-tenant Prometheus)

### Visualization

**Grafana** (self-hosted)
- Rich dashboards for metrics visualization
- Alerting built-in
- Multiple data source support
- Cost: $0 (self-hosted)

**Sample Dashboards**:
- Test Distribution Over Time (pie chart + trend)
- Test Duration Heatmap (by size and outcome)
- CI Performance Dashboard (duration, failures, resource usage)
- Coverage Trends (line chart with annotations for releases)

### Log Aggregation

**Loki** (self-hosted)
- Log aggregation optimized for Grafana
- Label-based indexing (cost-effective)
- Integrates with Prometheus/Grafana
- Cost: $0 (self-hosted)

**Alternative**:
- ELK Stack (Elasticsearch, Logstash, Kibana) - more features, higher resource usage

### Alerting

**AlertManager** (part of Prometheus)
- Route alerts to Slack, email, PagerDuty, etc.
- Grouping, inhibition, silencing
- Cost: $0 (self-hosted)

**Alternative**:
- Grafana OnCall (open-source on-call management)

## Metrics Collection

### Custom pytest Plugin Extension

Extend pytest-test-categories to emit metrics:

```python
# File: pytest_metrics_exporter.py
"""Prometheus exporter for pytest-test-categories metrics."""

from __future__ import annotations

import pytest
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, push_to_gateway

# Define metrics
TEST_DURATION = Histogram(
    'pytest_test_duration_seconds',
    'Test execution duration',
    ['size', 'outcome', 'project'],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 900.0]
)

TIMING_VIOLATIONS = Counter(
    'pytest_timing_violations_total',
    'Number of timing constraint violations',
    ['size', 'project']
)

TEST_DISTRIBUTION = Gauge(
    'pytest_test_size_distribution',
    'Distribution of tests by size',
    ['size', 'project']
)

def pytest_configure(config):
    """Register metrics plugin."""
    config.pluginmanager.register(MetricsPlugin(config), "metrics_plugin")

class MetricsPlugin:
    """Pytest plugin to export metrics to Prometheus."""

    def __init__(self, config):
        self.config = config
        self.project = config.getoption("--project-name", default="unknown")
        self.pushgateway_url = config.getoption("--metrics-pushgateway")

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        """Capture test outcomes and timing."""
        outcome = yield
        report = outcome.get_result()

        if report.when == "call":
            # Get test size marker
            size = "unknown"
            for marker in item.iter_markers():
                if marker.name in ["small", "medium", "large", "xlarge"]:
                    size = marker.name
                    break

            # Record duration
            TEST_DURATION.labels(
                size=size,
                outcome=report.outcome,
                project=self.project
            ).observe(report.duration)

            # Record timing violations
            if hasattr(report, 'timing_violation') and report.timing_violation:
                TIMING_VIOLATIONS.labels(
                    size=size,
                    project=self.project
                ).inc()

    def pytest_collection_finish(self, session):
        """Record test distribution metrics."""
        from pytest_test_categories.distribution.stats import DistributionStats

        # Count tests by size
        size_counts = {"small": 0, "medium": 0, "large": 0, "xlarge": 0}
        for item in session.items:
            for marker in item.iter_markers():
                if marker.name in size_counts:
                    size_counts[marker.name] += 1

        # Calculate percentages
        total = sum(size_counts.values())
        if total > 0:
            for size, count in size_counts.items():
                TEST_DISTRIBUTION.labels(
                    size=size,
                    project=self.project
                ).set(count / total)

    def pytest_sessionfinish(self, session, exitstatus):
        """Push metrics to Pushgateway after session."""
        if self.pushgateway_url:
            try:
                push_to_gateway(
                    self.pushgateway_url,
                    job=f'pytest_{self.project}',
                    registry=CollectorRegistry()
                )
            except Exception as e:
                print(f"Failed to push metrics: {e}")
```

**Usage in CI**:

```yaml
# GitHub Actions example
- name: Run tests with metrics
  run: |
    uv run pytest \
      --project-name=pytest-test-categories \
      --metrics-pushgateway=http://prometheus-pushgateway:9091
  env:
    PROMETHEUS_PUSHGATEWAY: ${{ secrets.PROMETHEUS_PUSHGATEWAY_URL }}
```

### Prometheus Pushgateway

For batch jobs (like CI runs), use Pushgateway:

```bash
# Run Pushgateway (self-hosted)
docker run -d -p 9091:9091 prom/pushgateway

# Prometheus scrapes Pushgateway
# Add to prometheus.yml:
scrape_configs:
  - job_name: 'pushgateway'
    honor_labels: true
    static_configs:
      - targets: ['pushgateway:9091']
```

**Cost**: $0 (self-hosted on spot instance, ~$5/month if using reserved instance)

## Alerting

### Sample Alert Rules

```yaml
# File: alerts/pytest_test_categories.yml
groups:
  - name: test_quality
    interval: 5m
    rules:
      # Test distribution alerts
      - alert: TestPyramidDegraded
        expr: pytest_test_size_distribution{size="small"} < 0.5
        for: 1h
        labels:
          severity: critical
          team: engineering
        annotations:
          summary: "Test pyramid degraded for {{ $labels.project }}"
          description: "Small test percentage is {{ $value | humanizePercentage }}, should be >80%"
          runbook: "https://github.com/mikelane/pytest-test-categories/wiki/TestPyramidRunbook"

      - alert: TooManyLargeTests
        expr: |
          (pytest_test_size_distribution{size="large"} +
           pytest_test_size_distribution{size="xlarge"}) > 0.1
        for: 2h
        labels:
          severity: warning
          team: engineering
        annotations:
          summary: "Excessive large tests in {{ $labels.project }}"
          description: "Large/XLarge tests are {{ $value | humanizePercentage }}, should be <8%"

      # Timing violation alerts
      - alert: FrequentTimingViolations
        expr: rate(pytest_timing_violations_total[1h]) > 0.1
        for: 30m
        labels:
          severity: warning
          team: engineering
        annotations:
          summary: "Frequent timing violations in {{ $labels.project }}"
          description: "{{ $value }} violations per second in {{ $labels.size }} tests"

      # CI performance alerts
      - alert: CITestSuiteSlow
        expr: |
          (ci_test_suite_duration_seconds > 300) or
          (ci_test_suite_duration_seconds / ci_test_suite_duration_seconds offset 7d > 1.3)
        for: 1h
        labels:
          severity: warning
          team: engineering
        annotations:
          summary: "CI test suite slow for {{ $labels.project }}"
          description: "Test suite duration: {{ $value }}s (30% increase from baseline)"

      # Coverage alerts
      - alert: CoverageBelowTarget
        expr: test_coverage_percentage < 100
        for: 5m
        labels:
          severity: critical
          team: engineering
        annotations:
          summary: "Test coverage below target for {{ $labels.project }}"
          description: "Coverage is {{ $value }}%, target is 100%"
```

### Alert Routing

```yaml
# AlertManager configuration
route:
  receiver: 'team-engineering-slack'
  group_by: ['alertname', 'project']
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 4h

  routes:
    - match:
        severity: critical
      receiver: 'team-engineering-pagerduty'
      continue: true

    - match:
        severity: warning
      receiver: 'team-engineering-slack'

receivers:
  - name: 'team-engineering-slack'
    slack_configs:
      - api_url: '<slack_webhook_url>'
        channel: '#engineering-alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

  - name: 'team-engineering-pagerduty'
    pagerduty_configs:
      - service_key: '<pagerduty_integration_key>'
```

**Cost**: $0 (Slack free tier, self-hosted AlertManager)

## Cost Optimization

### Retention Policies

Configure aggressive retention to minimize storage costs:

```yaml
# Prometheus retention (prometheus.yml)
storage:
  tsdb:
    retention.time: 15d  # Keep raw metrics for 15 days
    retention.size: 10GB

# Thanos (long-term storage)
# Downsample old data:
# - 5m resolution after 15 days
# - 1h resolution after 60 days
# - Delete after 1 year
```

**Cost Impact**: ~90% storage reduction with downsampling

### Sampling Strategies

Sample high-cardinality metrics:

```python
# Only record every 10th test duration for large test suites
if random.random() < 0.1:  # 10% sampling
    TEST_DURATION.labels(...).observe(duration)
```

**Cost Impact**: 90% reduction in metric ingestion

### Self-hosted Infrastructure

Run monitoring stack on spot/preemptible instances:

```bash
# AWS Spot Instance pricing
# t3.medium spot: ~$0.012/hour = $8.64/month
# vs on-demand: ~$0.0416/hour = $30/month

# Monthly cost for full stack:
# - Prometheus: $8.64
# - Grafana: $8.64
# - AlertManager: $4.32 (t3.small)
# - Loki: $8.64
# Total: ~$30/month (vs $300+/month for commercial SaaS)
```

### Storage Optimization

Use object storage for long-term metrics:

```yaml
# Thanos S3 configuration
type: S3
config:
  bucket: "thanos-metrics"
  endpoint: "s3.us-west-2.amazonaws.com"
  # Use S3 Intelligent-Tiering for automatic cost optimization
  storage_class: INTELLIGENT_TIERING
```

**Cost**: ~$0.50/month for 100GB metrics (S3 IA tier)

## Example Implementations

### Grafana Dashboard JSON

```json
{
  "dashboard": {
    "title": "pytest-test-categories - Test Health",
    "panels": [
      {
        "title": "Test Size Distribution",
        "type": "piechart",
        "targets": [
          {
            "expr": "pytest_test_size_distribution{project=\"$project\"}",
            "legendFormat": "{{ size }}"
          }
        ]
      },
      {
        "title": "Test Duration Heatmap",
        "type": "heatmap",
        "targets": [
          {
            "expr": "rate(pytest_test_duration_seconds_bucket{project=\"$project\"}[5m])",
            "legendFormat": "{{ size }} - {{ le }}"
          }
        ]
      },
      {
        "title": "Timing Violations (7d)",
        "type": "graph",
        "targets": [
          {
            "expr": "increase(pytest_timing_violations_total{project=\"$project\"}[7d])",
            "legendFormat": "{{ size }}"
          }
        ]
      }
    ]
  }
}
```

### CI Integration Example

```yaml
# .github/workflows/ci-with-metrics.yml
jobs:
  test-with-metrics:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install prometheus-client
          uv sync --all-groups

      - name: Run tests with metrics export
        run: |
          uv run pytest \
            --project-name=pytest-test-categories \
            --metrics-pushgateway=${{ secrets.PROMETHEUS_PUSHGATEWAY_URL }}
        env:
          CI: true

      - name: Export CI metrics
        if: always()
        run: |
          # Export test suite duration to Prometheus
          DURATION=${{ job.duration }}
          cat <<EOF | curl --data-binary @- \
            ${{ secrets.PROMETHEUS_PUSHGATEWAY_URL }}/metrics/job/ci_pipeline
          # TYPE ci_test_suite_duration_seconds gauge
          ci_test_suite_duration_seconds{project="pytest-test-categories",branch="${GITHUB_REF##*/}"} $DURATION
          EOF
```

## Recommendations

### For Small Teams (<10 developers)

**Minimal Setup**:
1. Enable GitHub Actions metrics (built-in, free)
2. Use test output parsing for basic metrics
3. Alert via GitHub Issues/Discussions
4. Manual review of trends weekly

**Cost**: $0/month

### For Medium Teams (10-50 developers)

**Self-hosted Stack**:
1. Prometheus + Grafana on single t3.medium spot instance
2. AlertManager for Slack notifications
3. Metrics collection via Pushgateway in CI
4. Weekly review dashboard in team meetings

**Cost**: ~$30/month

### For Large Teams (>50 developers)

**Scalable Infrastructure**:
1. Prometheus + Thanos for long-term storage
2. Grafana with multiple dashboards per team
3. Loki for log aggregation
4. AlertManager with PagerDuty integration
5. Dedicated SRE monitoring CI performance

**Cost**: ~$100-200/month (self-hosted on reserved instances)

## Additional Resources

- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [Grafana Dashboard Design](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/)
- [SLO/SLI/Error Budget for CI](https://sre.google/workbook/implementing-slos/)
