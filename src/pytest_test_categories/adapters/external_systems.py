"""Production external systems detector adapter using sys.modules inspection.

This module provides the production implementation of ExternalSystemsDetectorPort
that detects external system usage by inspecting sys.modules after test execution.

The ExternalSystemsDetector follows hexagonal architecture principles:
- Implements the ExternalSystemsDetectorPort interface (port)
- Inspects sys.modules to detect imports of testcontainers, docker, etc.
- Emits pytest warnings when external systems are detected in medium tests

Detection Strategy:
1. Before test execution: Snapshot sys.modules keys
2. After test execution: Compare with current sys.modules
3. Report any newly imported external system packages

Detected Packages:
- testcontainers (testcontainers-python for containerized testing)
- docker (docker SDK for Python)

Example:
    >>> detector = ExternalSystemsDetector()
    >>> try:
    ...     detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)
    ...     # Test runs, imports testcontainers
    ...     detected = detector.check_external_systems_detected()
    ...     if detected:
    ...         detector.on_external_systems_detected(detected, 'test::fn')
    ... finally:
    ...     detector.deactivate()

See Also:
    - ExternalSystemsDetectorPort: The abstract interface in ports/external_systems.py
    - FakeExternalSystemsDetector: Test adapter in adapters/fake_external_systems.py
    - DatabasePatchingBlocker: Similar production adapter pattern

"""

from __future__ import annotations

import sys
import warnings

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


class ExternalSystemsWarning(UserWarning):
    """Warning category for external systems detection in medium tests.

    This warning is emitted when a medium test imports packages that suggest
    use of external containerized systems (testcontainers, docker SDK, etc.).

    Per Google's test sizes table, external systems are "Discouraged" for
    medium tests, so this is a warning rather than an error.

    Example:
        >>> import warnings
        >>> warnings.warn(
        ...     'Medium test uses external systems',
        ...     ExternalSystemsWarning
        ... )

    """


class ExternalSystemsDetector(ExternalSystemsDetectorPort):
    """Production adapter that inspects sys.modules to detect external systems.

    This adapter detects external system usage by comparing sys.modules
    before and after test execution. When external system packages are
    detected in medium tests, it emits a warning.

    Attributes:
        state: Current detector state (inherited from ExternalSystemsDetectorPort).
        current_test_size: The test size set during activation.
        current_enforcement_mode: The enforcement mode set during activation.
        current_test_nodeid: The pytest node ID of the current test.
        _modules_snapshot: Snapshot of sys.modules keys before test execution.

    Example:
        >>> detector = ExternalSystemsDetector()
        >>> detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)
        >>> # Test imports testcontainers
        >>> detected = detector.check_external_systems_detected()
        >>> if detected:
        ...     detector.on_external_systems_detected(detected, 'test::fn')
        >>> detector.deactivate()

    """

    current_test_size: TestSize | None = Field(default=None, description='Test size')
    current_enforcement_mode: EnforcementMode | None = Field(default=None, description='Enforcement mode')
    current_test_nodeid: str = Field(default='', description='Test node ID')

    def model_post_init(self, context: object, /) -> None:  # noqa: ARG002
        """Initialize post-Pydantic setup, storing reference to modules snapshot."""
        object.__setattr__(self, '_modules_snapshot', set())

    def _do_activate(
        self,
        test_size: TestSize,
        enforcement_mode: EnforcementMode,
    ) -> None:
        """Snapshot sys.modules before test execution.

        Args:
            test_size: The size category of the current test.
            enforcement_mode: How to handle detections.

        """
        self.current_test_size = test_size
        self.current_enforcement_mode = enforcement_mode
        # Snapshot current modules to detect new imports during test
        object.__setattr__(self, '_modules_snapshot', set(sys.modules.keys()))

    def _do_deactivate(self) -> None:
        """Clear the modules snapshot."""
        object.__setattr__(self, '_modules_snapshot', set())

    def _do_check_external_systems_detected(self) -> set[str]:
        """Check sys.modules for external system packages.

        Compares current sys.modules with the snapshot taken during activation
        to detect newly imported packages that match EXTERNAL_SYSTEM_PACKAGES.

        Returns:
            Set of detected external system package names.

        """
        snapshot: set[str] = object.__getattribute__(self, '_modules_snapshot')
        current_modules = set(sys.modules.keys())

        # Find newly imported modules since activation
        new_modules = current_modules - snapshot

        # Check for external system packages (match top-level package)
        detected: set[str] = set()
        for module_name in new_modules:
            top_level = module_name.split('.')[0]
            if top_level in EXTERNAL_SYSTEM_PACKAGES:
                detected.add(top_level)

        return detected

    def _do_on_external_systems_detected(
        self,
        packages: set[str],
        test_nodeid: str,
    ) -> None:
        """Emit a pytest warning for detected external systems.

        This emits a UserWarning that pytest will capture and report.
        The warning includes guidance on suppressing or addressing the issue.

        Args:
            packages: The detected package names.
            test_nodeid: The pytest node ID of the test.

        """
        if self.current_enforcement_mode == EnforcementMode.OFF:
            return

        packages_str = ', '.join(sorted(packages))
        warning_message = (
            f"Medium test '{test_nodeid}' uses external system packages: {packages_str}. "
            'Per Google test sizes, external systems are DISCOURAGED for medium tests. '
            'Options:\n'
            '  1. Add @pytest.mark.medium(allow_external_systems=True) to suppress this warning\n'
            '  2. Move test to @pytest.mark.large if this is integration testing\n'
            '  3. Use mocks/fakes instead of real containers for faster, more reliable tests\n'
            'See: https://testing.googleblog.com/2010/12/test-sizes.html'
        )

        # Emit warning for both WARN and STRICT modes
        # External systems are DISCOURAGED (not prohibited) so always warn, never error
        if self.current_enforcement_mode in (EnforcementMode.WARN, EnforcementMode.STRICT):
            warnings.warn(warning_message, ExternalSystemsWarning, stacklevel=2)

    def reset(self) -> None:
        """Reset detector to initial state, clearing snapshot.

        This is safe to call regardless of current state.

        """
        object.__setattr__(self, '_modules_snapshot', set())
        super().reset()
        self.current_test_size = None
        self.current_enforcement_mode = None
        self.current_test_nodeid = ''

    @property
    def is_active(self) -> bool:
        """Check if detector is currently active.

        Returns:
            True if detector is in ACTIVE state, False otherwise.

        """
        return self.state == BlockerState.ACTIVE
