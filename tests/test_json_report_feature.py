"""Integration tests for JSON report export feature.

This module tests the end-to-end JSON report export functionality
using pytester to simulate real pytest runs.
"""

from __future__ import annotations

import json

import pytest


@pytest.mark.medium
class DescribeJsonReportExport:
    """Test suite for JSON report export feature."""

    def it_generates_json_report_with_json_option(self, pytester: pytest.Pytester) -> None:
        """Generate JSON report when --test-size-report=json is specified."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_small_one():
                assert True

            @pytest.mark.small
            def test_small_two():
                assert True

            @pytest.mark.medium
            def test_medium_one():
                assert True
            """
        )

        result = pytester.runpytest('--test-size-report=json')

        result.assert_outcomes(passed=3)
        output = result.stdout.str()
        assert '"version"' in output
        assert '"timestamp"' in output
        assert '"summary"' in output
        assert '"distribution"' in output

    def it_writes_json_report_to_file(self, pytester: pytest.Pytester) -> None:
        """Write JSON report to file when --test-size-report-file is specified."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_small():
                assert True

            @pytest.mark.medium
            def test_medium():
                assert True
            """
        )

        report_path = pytester.path / 'report.json'
        result = pytester.runpytest(
            '--test-size-report=json',
            f'--test-size-report-file={report_path}',
        )

        result.assert_outcomes(passed=2)
        assert report_path.exists()
        report_content = json.loads(report_path.read_text())
        assert 'version' in report_content
        assert 'summary' in report_content
        assert report_content['summary']['total_tests'] == 2

    def it_includes_distribution_statistics_in_json(self, pytester: pytest.Pytester) -> None:
        """Include distribution statistics in JSON output."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_small():
                assert True

            @pytest.mark.medium
            def test_medium():
                assert True

            @pytest.mark.large
            def test_large():
                assert True

            @pytest.mark.xlarge
            def test_xlarge():
                assert True
            """
        )

        report_path = pytester.path / 'report.json'
        result = pytester.runpytest(
            '--test-size-report=json',
            f'--test-size-report-file={report_path}',
        )

        result.assert_outcomes(passed=4)
        report = json.loads(report_path.read_text())
        distribution = report['summary']['distribution']

        assert distribution['small']['count'] == 1
        assert distribution['medium']['count'] == 1
        assert distribution['large']['count'] == 1
        assert distribution['xlarge']['count'] == 1

    def it_includes_per_test_details_in_json(self, pytester: pytest.Pytester) -> None:
        """Include per-test details in JSON output."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_small_one():
                assert True

            @pytest.mark.medium
            def test_medium_fail():
                assert False
            """
        )

        report_path = pytester.path / 'report.json'
        result = pytester.runpytest(
            '--test-size-report=json',
            f'--test-size-report-file={report_path}',
        )

        result.assert_outcomes(passed=1, failed=1)
        report = json.loads(report_path.read_text())

        assert len(report['tests']) == 2
        test_names = [t['name'] for t in report['tests']]
        assert any('test_small_one' in name for name in test_names)
        assert any('test_medium_fail' in name for name in test_names)

        failed_test = next(t for t in report['tests'] if 'fail' in t['name'])
        assert failed_test['status'] == 'failed'

    def it_includes_timing_violations_in_json(self, pytester: pytest.Pytester) -> None:
        """Include timing violations in JSON output."""
        pytester.makepyfile(
            test_slow="""
            import pytest
            import time

            @pytest.mark.small
            def test_slow():
                time.sleep(1.1)  # Exceeds small test limit of 1 second
                assert True

            @pytest.mark.small
            def test_fast():
                assert True
            """
        )

        report_path = pytester.path / 'report.json'
        pytester.runpytest(
            '--test-size-report=json',
            f'--test-size-report-file={report_path}',
        )

        report = json.loads(report_path.read_text())

        assert report['summary']['violations']['timing'] >= 1
        slow_test = next((t for t in report['tests'] if 'slow' in t['name']), None)
        if slow_test:
            assert 'timing' in slow_test['violations']

    def it_handles_unsized_tests_in_json(self, pytester: pytest.Pytester) -> None:
        """Handle unsized tests correctly in JSON output."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_small():
                assert True

            def test_unsized():
                assert True
            """
        )

        report_path = pytester.path / 'report.json'
        result = pytester.runpytest(
            '--test-size-report=json',
            f'--test-size-report-file={report_path}',
        )

        result.assert_outcomes(passed=2)
        report = json.loads(report_path.read_text())

        assert report['summary']['total_tests'] == 2
        unsized_test = next((t for t in report['tests'] if 'unsized' in t['name']), None)
        assert unsized_test is not None
        assert unsized_test['size'] == 'unsized'

    def it_includes_iso_timestamp_in_json(self, pytester: pytest.Pytester) -> None:
        """Include ISO 8601 formatted timestamp in JSON output."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_small():
                assert True
            """
        )

        report_path = pytester.path / 'report.json'
        result = pytester.runpytest(
            '--test-size-report=json',
            f'--test-size-report-file={report_path}',
        )

        result.assert_outcomes(passed=1)
        report = json.loads(report_path.read_text())

        timestamp = report['timestamp']
        assert 'T' in timestamp
        assert timestamp.endswith('Z')

    def it_handles_empty_test_suite_in_json(self, pytester: pytest.Pytester) -> None:
        """Handle empty test suite gracefully in JSON output."""
        empty_dir = pytester.mkpydir('empty')

        report_path = pytester.path / 'report.json'
        result = pytester.runpytest(
            '--test-size-report=json',
            f'--test-size-report-file={report_path}',
            str(empty_dir),
        )

        assert result.ret in [0, 5]  # 0 = success, 5 = no tests collected
        assert report_path.exists()
        report = json.loads(report_path.read_text())
        assert report['summary']['total_tests'] == 0
        assert len(report['tests']) == 0

    def it_backward_compatible_with_basic_report(self, pytester: pytest.Pytester) -> None:
        """Verify backward compatibility with basic report option."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_small():
                assert True
            """
        )

        result = pytester.runpytest('--test-size-report=basic')

        result.assert_outcomes(passed=1)
        result.stdout.fnmatch_lines(['*Test Size Report Summary*'])

    def it_backward_compatible_with_detailed_report(self, pytester: pytest.Pytester) -> None:
        """Verify backward compatibility with detailed report option."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_small():
                assert True
            """
        )

        result = pytester.runpytest('--test-size-report=detailed')

        result.assert_outcomes(passed=1)
        result.stdout.fnmatch_lines(['*Detailed Test Size Report*'])


@pytest.mark.medium
class DescribeJsonReportFileOption:
    """Test suite for --test-size-report-file option."""

    def it_requires_json_report_format(self, pytester: pytest.Pytester) -> None:
        """Warn when --test-size-report-file used without --test-size-report=json."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_small():
                assert True
            """
        )

        report_path = pytester.path / 'report.json'
        result = pytester.runpytest(
            '--test-size-report=basic',
            f'--test-size-report-file={report_path}',
        )

        result.assert_outcomes(passed=1)
        assert not report_path.exists()

    def it_creates_parent_directories_if_needed(self, pytester: pytest.Pytester) -> None:
        """Create parent directories for report file if they do not exist."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_small():
                assert True
            """
        )

        report_path = pytester.path / 'nested' / 'dir' / 'report.json'
        result = pytester.runpytest(
            '--test-size-report=json',
            f'--test-size-report-file={report_path}',
        )

        result.assert_outcomes(passed=1)
        assert report_path.exists()


@pytest.mark.medium
class DescribeJsonReportHermeticityViolations:
    """Test suite for hermeticity violation tracking in JSON reports."""

    def it_includes_hermeticity_violations_summary_in_json(self, pytester: pytest.Pytester) -> None:
        """Include hermeticity violations summary structure in JSON output."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_small():
                assert True
            """
        )

        report_path = pytester.path / 'report.json'
        result = pytester.runpytest(
            '--test-size-report=json',
            f'--test-size-report-file={report_path}',
        )

        result.assert_outcomes(passed=1)
        report = json.loads(report_path.read_text())

        hermeticity = report['summary']['violations']['hermeticity']
        assert 'network' in hermeticity
        assert 'filesystem' in hermeticity
        assert 'process' in hermeticity
        assert 'database' in hermeticity
        assert 'sleep' in hermeticity
        assert 'total' in hermeticity

    def it_tracks_network_violations_in_warn_mode(self, pytester: pytest.Pytester) -> None:
        """Track network violations in warn mode."""
        pytester.makepyfile(
            test_network="""
            import pytest
            import socket

            @pytest.mark.small
            def test_network_violation():
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.connect(('httpbin.org', 80))
                    s.close()
                except Exception:
                    pass
                assert True
            """
        )

        report_path = pytester.path / 'report.json'
        result = pytester.runpytest(
            '--test-size-report=json',
            f'--test-size-report-file={report_path}',
            '--test-categories-enforcement=warn',
        )

        result.assert_outcomes(passed=1)
        report = json.loads(report_path.read_text())

        assert report['summary']['violations']['hermeticity']['network'] >= 1
        assert report['summary']['violations']['hermeticity']['total'] >= 1

    def it_includes_hermeticity_violations_in_test_details(self, pytester: pytest.Pytester) -> None:
        """Include hermeticity violations in per-test details."""
        pytester.makepyfile(
            test_network="""
            import pytest
            import socket

            @pytest.mark.small
            def test_network_violation():
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.connect(('httpbin.org', 80))
                    s.close()
                except Exception:
                    pass
                assert True
            """
        )

        report_path = pytester.path / 'report.json'
        result = pytester.runpytest(
            '--test-size-report=json',
            f'--test-size-report-file={report_path}',
            '--test-categories-enforcement=warn',
        )

        result.assert_outcomes(passed=1)
        report = json.loads(report_path.read_text())

        test_entry = next((t for t in report['tests'] if 'network_violation' in t['name']), None)
        assert test_entry is not None
        assert any('hermeticity:network' in v for v in test_entry['violations'])

    def it_has_zero_violations_when_enforcement_off(self, pytester: pytest.Pytester) -> None:
        """Report zero violations when enforcement is off."""
        pytester.makepyfile(
            test_network="""
            import pytest
            import socket

            @pytest.mark.small
            def test_network_access():
                # Network access but enforcement is off
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.close()
                assert True
            """
        )

        report_path = pytester.path / 'report.json'
        result = pytester.runpytest(
            '--test-size-report=json',
            f'--test-size-report-file={report_path}',
            '--test-categories-enforcement=off',
        )

        result.assert_outcomes(passed=1)
        report = json.loads(report_path.read_text())

        assert report['summary']['violations']['hermeticity']['total'] == 0

    def it_tracks_sleep_violations_in_warn_mode(self, pytester: pytest.Pytester) -> None:
        """Track sleep violations in warn mode."""
        pytester.makepyfile(
            test_sleep="""
            import pytest
            import time

            @pytest.mark.small
            def test_sleep_violation():
                time.sleep(0.01)
                assert True
            """
        )

        report_path = pytester.path / 'report.json'
        result = pytester.runpytest(
            '--test-size-report=json',
            f'--test-size-report-file={report_path}',
            '--test-categories-enforcement=warn',
        )

        result.assert_outcomes(passed=1)
        report = json.loads(report_path.read_text())

        assert report['summary']['violations']['hermeticity']['sleep'] >= 1

    def it_tracks_database_violations_in_warn_mode(self, pytester: pytest.Pytester) -> None:
        """Track database violations in warn mode."""
        pytester.makepyfile(
            test_database="""
            import pytest
            import sqlite3

            @pytest.mark.small
            def test_database_violation():
                conn = sqlite3.connect(':memory:')
                conn.close()
                assert True
            """
        )

        report_path = pytester.path / 'report.json'
        result = pytester.runpytest(
            '--test-size-report=json',
            f'--test-size-report-file={report_path}',
            '--test-categories-enforcement=warn',
        )

        result.assert_outcomes(passed=1)
        report = json.loads(report_path.read_text())

        assert report['summary']['violations']['hermeticity']['database'] >= 1
