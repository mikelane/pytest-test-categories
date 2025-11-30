"""Test the external systems detection adapters.

This module tests both the FakeExternalSystemsDetector (test adapter) and
ExternalSystemsDetector (production adapter) implementations.

The external systems detectors follow hexagonal architecture:
- ExternalSystemsDetectorPort is the Port (interface)
- FakeExternalSystemsDetector is a Test Adapter (test double)
- ExternalSystemsDetector is a Production Adapter (real implementation)

This follows the same pattern as the database, network, and filesystem blocker modules.

External systems detection warns when medium tests use:
- testcontainers (testcontainers-python)
- docker (docker SDK)

Per Google's test sizes, external systems are DISCOURAGED (not prohibited)
for medium tests, so we emit warnings rather than errors.
"""

from __future__ import annotations

import sys

import pytest
from icontract import ViolationError

from pytest_test_categories.adapters.external_systems import (
    ExternalSystemsDetector,
    ExternalSystemsWarning,
)
from pytest_test_categories.adapters.fake_external_systems import FakeExternalSystemsDetector
from pytest_test_categories.ports.external_systems import EXTERNAL_SYSTEM_PACKAGES
from pytest_test_categories.ports.network import (
    BlockerState,
    EnforcementMode,
)
from pytest_test_categories.types import TestSize


@pytest.mark.small
class DescribeFakeExternalSystemsDetector:
    """Tests for the FakeExternalSystemsDetector test double."""

    def it_starts_in_inactive_state(self) -> None:
        """Verify the detector initializes in INACTIVE state."""
        detector = FakeExternalSystemsDetector()

        assert detector.state == BlockerState.INACTIVE

    def it_transitions_to_active_on_activate(self) -> None:
        """Verify activate() transitions from INACTIVE to ACTIVE."""
        detector = FakeExternalSystemsDetector()

        detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        assert detector.state == BlockerState.ACTIVE

    def it_transitions_to_inactive_on_deactivate(self) -> None:
        """Verify deactivate() transitions from ACTIVE to INACTIVE."""
        detector = FakeExternalSystemsDetector()
        detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        detector.deactivate()

        assert detector.state == BlockerState.INACTIVE

    def it_fails_to_activate_when_already_active(self) -> None:
        """Verify activate() raises when already ACTIVE."""
        detector = FakeExternalSystemsDetector()
        detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        with pytest.raises(ViolationError, match='INACTIVE'):
            detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)

    def it_fails_to_deactivate_when_inactive(self) -> None:
        """Verify deactivate() raises when already INACTIVE."""
        detector = FakeExternalSystemsDetector()

        with pytest.raises(ViolationError, match='ACTIVE'):
            detector.deactivate()

    def it_records_activation_parameters(self) -> None:
        """Verify the detector records test size and enforcement mode."""
        detector = FakeExternalSystemsDetector()

        detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        assert detector.current_test_size == TestSize.MEDIUM
        assert detector.current_enforcement_mode == EnforcementMode.WARN

    def it_detects_simulated_testcontainers_import(self) -> None:
        """Verify simulated testcontainers import is detected."""
        detector = FakeExternalSystemsDetector()
        detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        detector.simulate_import('testcontainers')
        detected = detector.check_external_systems_detected()

        assert detected == {'testcontainers'}

    def it_detects_simulated_docker_import(self) -> None:
        """Verify simulated docker import is detected."""
        detector = FakeExternalSystemsDetector()
        detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        detector.simulate_import('docker')
        detected = detector.check_external_systems_detected()

        assert detected == {'docker'}

    def it_detects_multiple_external_packages(self) -> None:
        """Verify multiple external system imports are detected."""
        detector = FakeExternalSystemsDetector()
        detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        detector.simulate_import('testcontainers')
        detector.simulate_import('docker')
        detected = detector.check_external_systems_detected()

        assert detected == {'testcontainers', 'docker'}

    def it_ignores_non_external_system_imports(self) -> None:
        """Verify non-external system imports are not detected."""
        detector = FakeExternalSystemsDetector()
        detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        detector.simulate_import('requests')
        detector.simulate_import('json')
        detected = detector.check_external_systems_detected()

        assert detected == set()

    def it_records_warning_in_warn_mode(self) -> None:
        """Verify on_external_systems_detected records warning in WARN mode."""
        detector = FakeExternalSystemsDetector()
        detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        detector.on_external_systems_detected({'testcontainers'}, 'test_module.py::test_fn')

        assert len(detector.warnings) == 1
        assert 'testcontainers' in detector.warnings[0]
        assert 'test_module.py::test_fn' in detector.warnings[0]

    def it_records_warning_in_strict_mode(self) -> None:
        """Verify on_external_systems_detected records warning in STRICT mode.

        External systems are DISCOURAGED (not prohibited) for medium tests,
        so we always warn even in STRICT mode - never raise an error.
        """
        detector = FakeExternalSystemsDetector()
        detector.activate(TestSize.MEDIUM, EnforcementMode.STRICT)

        detector.on_external_systems_detected({'testcontainers'}, 'test_module.py::test_fn')

        assert len(detector.warnings) == 1
        assert 'testcontainers' in detector.warnings[0]

    def it_does_not_record_warning_in_off_mode(self) -> None:
        """Verify on_external_systems_detected does nothing in OFF mode."""
        detector = FakeExternalSystemsDetector()
        detector.activate(TestSize.MEDIUM, EnforcementMode.OFF)

        detector.on_external_systems_detected({'testcontainers'}, 'test_module.py::test_fn')

        assert len(detector.warnings) == 0

    def it_fails_check_when_inactive(self) -> None:
        """Verify check_external_systems_detected raises when INACTIVE."""
        detector = FakeExternalSystemsDetector()

        with pytest.raises(ViolationError, match='ACTIVE'):
            detector.check_external_systems_detected()

    def it_fails_on_detection_when_inactive(self) -> None:
        """Verify on_external_systems_detected raises when INACTIVE."""
        detector = FakeExternalSystemsDetector()

        with pytest.raises(ViolationError, match='ACTIVE'):
            detector.on_external_systems_detected({'testcontainers'}, 'test::fn')

    def it_resets_to_initial_state(self) -> None:
        """Verify reset() returns detector to initial state."""
        detector = FakeExternalSystemsDetector()
        detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)
        detector.simulate_import('testcontainers')
        detector.on_external_systems_detected({'testcontainers'}, 'test::fn')

        detector.reset()

        assert detector.state == BlockerState.INACTIVE
        assert detector.current_test_size is None
        assert detector.current_enforcement_mode is None
        assert len(detector.simulated_imports) == 0
        assert len(detector.warnings) == 0

    def it_resets_even_when_active(self) -> None:
        """Verify reset() works regardless of current state."""
        detector = FakeExternalSystemsDetector()
        detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        detector.reset()

        assert detector.state == BlockerState.INACTIVE

    def it_tracks_call_counts(self) -> None:
        """Verify the detector tracks method invocation counts."""
        detector = FakeExternalSystemsDetector()

        detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)
        detector.check_external_systems_detected()
        detector.check_external_systems_detected()
        detector.deactivate()

        assert detector.activate_count == 1
        assert detector.deactivate_count == 1
        assert detector.check_count == 2

    def it_clears_simulated_imports(self) -> None:
        """Verify clear_simulated_imports removes all simulated imports."""
        detector = FakeExternalSystemsDetector()
        detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)
        detector.simulate_import('testcontainers')
        detector.simulate_import('docker')

        detector.clear_simulated_imports()

        assert len(detector.simulated_imports) == 0

    def it_reports_is_active_correctly(self) -> None:
        """Verify is_active property reflects state."""
        detector = FakeExternalSystemsDetector()

        assert detector.is_active is False

        detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)
        assert detector.is_active is True

        detector.deactivate()  # type: ignore[unreachable]  # mypy doesn't understand icontract @require
        assert detector.is_active is False


@pytest.mark.small
class DescribeExternalSystemsDetector:
    """Tests for the ExternalSystemsDetector production adapter."""

    def it_starts_in_inactive_state(self) -> None:
        """Verify the detector initializes in INACTIVE state."""
        detector = ExternalSystemsDetector()

        assert detector.state == BlockerState.INACTIVE

    def it_transitions_to_active_on_activate(self) -> None:
        """Verify activate() transitions from INACTIVE to ACTIVE."""
        detector = ExternalSystemsDetector()

        detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        assert detector.state == BlockerState.ACTIVE

        detector.deactivate()

    def it_transitions_to_inactive_on_deactivate(self) -> None:
        """Verify deactivate() transitions from ACTIVE to INACTIVE."""
        detector = ExternalSystemsDetector()
        detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        detector.deactivate()

        assert detector.state == BlockerState.INACTIVE

    def it_fails_to_activate_when_already_active(self) -> None:
        """Verify activate() raises when already ACTIVE."""
        detector = ExternalSystemsDetector()
        detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        try:
            with pytest.raises(ViolationError, match='INACTIVE'):
                detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)
        finally:
            detector.reset()

    def it_fails_to_deactivate_when_inactive(self) -> None:
        """Verify deactivate() raises when already INACTIVE."""
        detector = ExternalSystemsDetector()

        with pytest.raises(ViolationError, match='ACTIVE'):
            detector.deactivate()

    def it_stores_activation_parameters(self) -> None:
        """Verify the detector stores test size and enforcement mode."""
        detector = ExternalSystemsDetector()

        detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        assert detector.current_test_size == TestSize.MEDIUM
        assert detector.current_enforcement_mode == EnforcementMode.WARN

        detector.deactivate()

    def it_returns_empty_set_when_no_external_systems_imported(self) -> None:
        """Verify no detection when no external systems are imported."""
        detector = ExternalSystemsDetector()
        detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        detected = detector.check_external_systems_detected()

        assert detected == set()

        detector.deactivate()

    def it_resets_to_initial_state(self) -> None:
        """Verify reset() returns detector to initial state."""
        detector = ExternalSystemsDetector()
        detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        detector.reset()

        assert detector.state == BlockerState.INACTIVE
        assert detector.current_test_size is None
        assert detector.current_enforcement_mode is None

    def it_emits_warning_in_warn_mode(self) -> None:
        """Verify on_external_systems_detected emits warning in WARN mode."""
        detector = ExternalSystemsDetector()
        detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        with pytest.warns(ExternalSystemsWarning, match='testcontainers'):
            detector.on_external_systems_detected({'testcontainers'}, 'test_module.py::test_fn')

        detector.deactivate()

    def it_emits_warning_in_strict_mode(self) -> None:
        """Verify on_external_systems_detected emits warning in STRICT mode.

        External systems are DISCOURAGED (not prohibited) for medium tests,
        so we always warn even in STRICT mode - never raise an error.
        """
        detector = ExternalSystemsDetector()
        detector.activate(TestSize.MEDIUM, EnforcementMode.STRICT)

        with pytest.warns(ExternalSystemsWarning, match='testcontainers'):
            detector.on_external_systems_detected({'testcontainers'}, 'test_module.py::test_fn')

        detector.deactivate()

    def it_does_not_emit_warning_in_off_mode(self) -> None:
        """Verify on_external_systems_detected does nothing in OFF mode."""
        detector = ExternalSystemsDetector()
        detector.activate(TestSize.MEDIUM, EnforcementMode.OFF)

        # This verifies no warning is emitted
        detector.on_external_systems_detected({'testcontainers'}, 'test_module.py::test_fn')

        detector.deactivate()

    def it_reports_is_active_correctly(self) -> None:
        """Verify is_active property reflects state."""
        detector = ExternalSystemsDetector()

        assert detector.is_active is False

        detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)
        assert detector.is_active is True

        detector.deactivate()  # type: ignore[unreachable]  # mypy doesn't understand icontract @require
        assert detector.is_active is False


@pytest.mark.small
class DescribeExternalSystemPackages:
    """Tests for the EXTERNAL_SYSTEM_PACKAGES constant."""

    def it_includes_testcontainers(self) -> None:
        """Verify testcontainers is in the packages list."""
        assert 'testcontainers' in EXTERNAL_SYSTEM_PACKAGES

    def it_includes_docker(self) -> None:
        """Verify docker is in the packages list."""
        assert 'docker' in EXTERNAL_SYSTEM_PACKAGES

    def it_is_a_frozenset(self) -> None:
        """Verify the packages list is immutable."""
        assert isinstance(EXTERNAL_SYSTEM_PACKAGES, frozenset)


@pytest.mark.small
class DescribeExternalSystemsWarning:
    """Tests for the ExternalSystemsWarning class."""

    def it_is_a_user_warning(self) -> None:
        """Verify ExternalSystemsWarning is a UserWarning subclass."""
        assert issubclass(ExternalSystemsWarning, UserWarning)

    def it_can_be_raised(self) -> None:
        """Verify the warning can be raised and caught."""
        import warnings

        with pytest.warns(ExternalSystemsWarning, match='test message'):
            warnings.warn('test message', ExternalSystemsWarning, stacklevel=2)


@pytest.mark.small
class DescribeExternalSystemsDetectorModulesInspection:
    """Tests that verify sys.modules inspection behavior."""

    def it_takes_snapshot_on_activation(self) -> None:
        """Verify activation takes a snapshot of current modules."""
        detector = ExternalSystemsDetector()
        initial_modules = set(sys.modules.keys())

        detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        # The snapshot is stored internally
        snapshot: set[str] = object.__getattribute__(detector, '_modules_snapshot')
        assert snapshot == initial_modules

        detector.deactivate()

    def it_clears_snapshot_on_deactivation(self) -> None:
        """Verify deactivation clears the modules snapshot."""
        detector = ExternalSystemsDetector()
        detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        detector.deactivate()

        snapshot: set[str] = object.__getattribute__(detector, '_modules_snapshot')
        assert snapshot == set()

    def it_clears_snapshot_on_reset(self) -> None:
        """Verify reset clears the modules snapshot."""
        detector = ExternalSystemsDetector()
        detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        detector.reset()

        snapshot: set[str] = object.__getattribute__(detector, '_modules_snapshot')
        assert snapshot == set()

    def it_detects_newly_imported_external_packages(self, mocker: object) -> None:
        """Verify detection of newly imported external system packages.

        This test simulates an import by directly manipulating sys.modules.
        """
        detector = ExternalSystemsDetector()
        detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        # Simulate a new import by adding to sys.modules
        # Use a unique fake module name based on testcontainers
        fake_module_name = 'testcontainers._test_fake_module'
        sys.modules[fake_module_name] = type(sys)('fake_module')

        try:
            detected = detector.check_external_systems_detected()
            # The top-level package 'testcontainers' is detected
            assert 'testcontainers' in detected
        finally:
            # Clean up
            del sys.modules[fake_module_name]
            detector.deactivate()

    def it_ignores_modules_that_were_already_imported(self) -> None:
        """Verify modules present before activation are not detected."""
        detector = ExternalSystemsDetector()

        # 'sys' is already imported, ensure it's not detected as external
        detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)
        detected = detector.check_external_systems_detected()

        assert 'sys' not in detected
        assert detected == set()

        detector.deactivate()
