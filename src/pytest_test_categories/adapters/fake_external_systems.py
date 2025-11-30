"""Fake external systems detector adapter for testing.

This module provides a test double implementation of ExternalSystemsDetectorPort
that allows unit testing without actual sys.modules inspection.

The FakeExternalSystemsDetector provides:
- Controllable simulation of external system imports
- Recording of detection events for assertions
- Call counting for verification

Example:
    >>> detector = FakeExternalSystemsDetector()
    >>> detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)
    >>> detector.simulate_import('testcontainers')
    >>> assert detector.check_external_systems_detected() == {'testcontainers'}
    >>> detector.deactivate()

See Also:
    - ExternalSystemsDetectorPort: The abstract interface in ports/external_systems.py
    - ExternalSystemsDetector: Production adapter (inspects sys.modules)
    - FakeDatabaseBlocker: Similar test adapter pattern

"""

from __future__ import annotations

from pydantic import Field

from pytest_test_categories.ports.external_systems import (
    EXTERNAL_SYSTEM_PACKAGES,
    ExternalSystemsDetectorPort,
)
from pytest_test_categories.ports.network import (
    BlockerState,
    EnforcementMode,
)
from pytest_test_categories.types import TestSize


class FakeExternalSystemsDetector(ExternalSystemsDetectorPort):
    """Test double for ExternalSystemsDetectorPort.

    This adapter provides controllable behavior for testing code that
    interacts with external systems detection without actually inspecting
    sys.modules.

    Attributes:
        state: Current detector state (inherited from ExternalSystemsDetectorPort).
        current_test_size: The test size set during activation.
        current_enforcement_mode: The enforcement mode set during activation.
        simulated_imports: Set of package names simulating imports.
        warnings: List of warning messages that would have been emitted.
        activate_count: Number of times activate() was called.
        deactivate_count: Number of times deactivate() was called.
        check_count: Number of times check_external_systems_detected() was called.

    Example:
        >>> detector = FakeExternalSystemsDetector()
        >>> detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)
        >>> detector.simulate_import('testcontainers')
        >>> detected = detector.check_external_systems_detected()
        >>> assert detected == {'testcontainers'}
        >>> detector.on_external_systems_detected(detected, 'test::fn')
        >>> assert len(detector.warnings) == 1

    """

    current_test_size: TestSize | None = Field(default=None, description='Test size')
    current_enforcement_mode: EnforcementMode | None = Field(default=None, description='Enforcement mode')
    simulated_imports: set[str] = Field(default_factory=set, description='Simulated external system imports')
    warnings: list[str] = Field(default_factory=list, description='Recorded warnings')
    activate_count: int = Field(default=0, description='Activation call count')
    deactivate_count: int = Field(default=0, description='Deactivation call count')
    check_count: int = Field(default=0, description='Check call count')

    def _do_activate(
        self,
        test_size: TestSize,
        enforcement_mode: EnforcementMode,
    ) -> None:
        """Record activation parameters for testing.

        Args:
            test_size: The size category of the current test.
            enforcement_mode: How to handle detections.

        """
        self.current_test_size = test_size
        self.current_enforcement_mode = enforcement_mode
        self.activate_count += 1

    def _do_deactivate(self) -> None:
        """Record deactivation for testing."""
        self.deactivate_count += 1

    def _do_check_external_systems_detected(self) -> set[str]:
        """Return simulated imports that match external system packages.

        Returns:
            Set of detected package names from simulated imports.

        """
        self.check_count += 1
        return self.simulated_imports & EXTERNAL_SYSTEM_PACKAGES

    def _do_on_external_systems_detected(
        self,
        packages: set[str],
        test_nodeid: str,
    ) -> None:
        """Record warning for testing.

        Args:
            packages: The detected package names.
            test_nodeid: The pytest node ID of the test.

        """
        # Record warning for both WARN and STRICT modes
        # External systems are DISCOURAGED (not prohibited) so always warn, never error
        if self.current_enforcement_mode in (EnforcementMode.WARN, EnforcementMode.STRICT):
            warning_msg = (
                f"Medium test '{test_nodeid}' uses external system packages: {sorted(packages)}. "
                'External systems are discouraged for medium tests. '
                'Consider using @pytest.mark.medium(allow_external_systems=True) to suppress this warning, '
                'or move to @pytest.mark.large if this is integration testing.'
            )
            self.warnings.append(warning_msg)

    def simulate_import(self, package: str) -> None:
        """Simulate an import of an external system package.

        This method allows tests to simulate the import of packages
        without actually importing them.

        Args:
            package: The package name to simulate importing.

        Example:
            >>> detector.simulate_import('testcontainers')
            >>> detector.simulate_import('docker')

        """
        self.simulated_imports.add(package)

    def clear_simulated_imports(self) -> None:
        """Clear all simulated imports.

        Example:
            >>> detector.simulate_import('testcontainers')
            >>> detector.clear_simulated_imports()
            >>> assert len(detector.simulated_imports) == 0

        """
        self.simulated_imports.clear()

    def reset(self) -> None:
        """Reset detector to initial state, clearing all recorded data.

        This is safe to call regardless of current state.

        """
        super().reset()
        self.current_test_size = None
        self.current_enforcement_mode = None
        self.simulated_imports = set()
        self.warnings = []
        self.activate_count = 0
        self.deactivate_count = 0
        self.check_count = 0

    @property
    def is_active(self) -> bool:
        """Check if detector is currently active.

        Returns:
            True if detector is in ACTIVE state, False otherwise.

        """
        return self.state == BlockerState.ACTIVE
