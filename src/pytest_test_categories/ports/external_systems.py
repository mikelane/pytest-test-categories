"""External systems detection port interface for medium test warnings.

This module defines the abstract interface (port) for detecting external system
usage during test execution. Following hexagonal architecture, this port defines
WHAT operations are available, while adapters define HOW they are implemented.

Per Google's test sizes table, "Use external systems" is **Discouraged** (not
prohibited) for medium tests. This module provides a warning mechanism when
medium tests appear to use external containerized systems.

The pattern enables:
- Production adapter (`ExternalSystemsDetector`): Inspects sys.modules to detect
  imports of testcontainers, docker, and similar libraries
- Test adapter (`FakeExternalSystemsDetector`): Controllable test double for
  unit testing

Detection targets:
- testcontainers package (testcontainers-python)
- docker SDK (docker-py)
- Additional container orchestration libraries

Example:
    Production usage (via plugin hooks):
    >>> detector = ExternalSystemsDetector()
    >>> detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)
    >>> # Test runs, imports testcontainers
    >>> if detector.check_external_systems_detected():
    ...     detector.on_external_systems_detected('test_module.py::test_fn')
    >>> detector.deactivate()

    Test usage:
    >>> detector = FakeExternalSystemsDetector()
    >>> detector.simulate_import('testcontainers')
    >>> assert detector.check_external_systems_detected()

See Also:
    - Google's Test Sizes: https://testing.googleblog.com/2010/12/test-sizes.html
    - DatabaseBlockerPort: Similar pattern in ports/database.py
    - NetworkBlockerPort: Similar pattern in ports/network.py

"""

from __future__ import annotations

from abc import (
    ABC,
    abstractmethod,
)
from typing import TYPE_CHECKING

from icontract import (
    ensure,
    require,
)
from pydantic import BaseModel

from pytest_test_categories.ports.network import (
    BlockerState,
    EnforcementMode,
)

if TYPE_CHECKING:
    from pytest_test_categories.types import TestSize


# External system packages that trigger warnings for medium tests
EXTERNAL_SYSTEM_PACKAGES = frozenset(
    {
        'testcontainers',
        'docker',
    }
)


class ExternalSystemsDetectorPort(BaseModel, ABC):
    """Abstract port defining external systems detection behavior.

    This port defines the contract for detecting external system usage during
    test execution. Implementations (adapters) provide the actual detection
    mechanism.

    Following hexagonal architecture:
    - This port defines WHAT operations are available
    - Adapters define HOW they are implemented
    - Production adapter: ExternalSystemsDetector (inspects sys.modules)
    - Test adapter: FakeExternalSystemsDetector (records simulated imports)

    The detector follows a state machine pattern:
    - INACTIVE: Not monitoring (initial state)
    - ACTIVE: Monitoring for external system imports

    State transitions are guarded by icontract preconditions/postconditions,
    following the same pattern as other port interfaces in this project.

    Attributes:
        state: Current detector state (INACTIVE or ACTIVE).

    Example:
        >>> class FakeExternalSystemsDetector(ExternalSystemsDetectorPort):
        ...     def _do_activate(self, test_size, enforcement_mode):
        ...         pass
        ...
        >>> detector = FakeExternalSystemsDetector()
        >>> assert detector.state == BlockerState.INACTIVE
        >>> detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)
        >>> assert detector.state == BlockerState.ACTIVE

    See Also:
        - DatabaseBlockerPort: Similar pattern in ports/database.py
        - NetworkBlockerPort: Similar pattern in ports/network.py

    """

    state: BlockerState = BlockerState.INACTIVE

    @require(lambda self: self.state == BlockerState.INACTIVE, 'Detector must be INACTIVE to activate')
    @ensure(lambda self: self.state == BlockerState.ACTIVE, 'Detector must be ACTIVE after activation')
    def activate(self, test_size: TestSize, enforcement_mode: EnforcementMode) -> None:
        """Activate external systems detection for a test.

        Transitions the detector from INACTIVE to ACTIVE state. Once active,
        the detector will monitor for external system imports.

        Args:
            test_size: The size category of the current test.
            enforcement_mode: How to handle detections (WARN or OFF).

        Raises:
            icontract.ViolationError: If detector is not in INACTIVE state.

        Example:
            >>> detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)
            >>> # Now imports of testcontainers/docker will be detected

        """
        self._do_activate(test_size, enforcement_mode)
        self.state = BlockerState.ACTIVE

    @abstractmethod
    def _do_activate(self, test_size: TestSize, enforcement_mode: EnforcementMode) -> None:
        """Perform adapter-specific activation logic.

        Subclasses implement this to perform adapter-specific activation.
        State transition is handled by the base class.

        Args:
            test_size: The size category of the current test.
            enforcement_mode: How to handle detections.

        """

    @require(lambda self: self.state == BlockerState.ACTIVE, 'Detector must be ACTIVE to deactivate')
    @ensure(lambda self: self.state == BlockerState.INACTIVE, 'Detector must be INACTIVE after deactivation')
    def deactivate(self) -> None:
        """Deactivate external systems detection.

        Transitions the detector from ACTIVE to INACTIVE state.

        Raises:
            icontract.ViolationError: If detector is not in ACTIVE state.

        Example:
            >>> try:
            ...     detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)
            ...     # test runs
            ... finally:
            ...     detector.deactivate()

        """
        self._do_deactivate()
        self.state = BlockerState.INACTIVE

    @abstractmethod
    def _do_deactivate(self) -> None:
        """Perform adapter-specific deactivation logic.

        Subclasses implement this to perform adapter-specific deactivation.
        State transition is handled by the base class.

        """

    @require(lambda self: self.state == BlockerState.ACTIVE, 'Detector must be ACTIVE to check')
    def check_external_systems_detected(self) -> set[str]:
        """Check if any external system packages have been imported.

        Returns:
            A set of detected package names that were imported during the test.

        Raises:
            icontract.ViolationError: If detector is not in ACTIVE state.

        Example:
            >>> detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)
            >>> detected = detector.check_external_systems_detected()
            >>> if detected:
            ...     print(f'Detected: {detected}')

        """
        return self._do_check_external_systems_detected()

    @abstractmethod
    def _do_check_external_systems_detected(self) -> set[str]:
        """Determine which external system packages were imported.

        Subclasses implement this to check for external system imports.

        Returns:
            A set of detected package names.

        """

    @require(lambda self: self.state == BlockerState.ACTIVE, 'Detector must be ACTIVE to handle detections')
    def on_external_systems_detected(
        self,
        packages: set[str],
        test_nodeid: str,
    ) -> None:
        """Handle detection of external system usage.

        Called when external system packages are detected in a medium test.
        The response is always a WARNING (not an error) because external
        systems are discouraged but not prohibited for medium tests.

        Args:
            packages: The detected package names.
            test_nodeid: The pytest node ID of the test.

        Raises:
            icontract.ViolationError: If detector is not in ACTIVE state.

        Example:
            >>> detector.activate(TestSize.MEDIUM, EnforcementMode.WARN)
            >>> detected = detector.check_external_systems_detected()
            >>> if detected:
            ...     detector.on_external_systems_detected(detected, 'test::fn')

        """
        self._do_on_external_systems_detected(packages, test_nodeid)

    @abstractmethod
    def _do_on_external_systems_detected(
        self,
        packages: set[str],
        test_nodeid: str,
    ) -> None:
        """Handle external system detection according to enforcement mode.

        Subclasses implement this to emit warnings.

        Args:
            packages: The detected package names.
            test_nodeid: The pytest node ID of the test.

        """

    def reset(self) -> None:
        """Reset detector to initial INACTIVE state.

        This is a convenience method for cleanup and testing. Unlike
        deactivate(), this does not require the detector to be in ACTIVE
        state - it unconditionally resets to INACTIVE.

        Example:
            >>> detector.reset()
            >>> assert detector.state == BlockerState.INACTIVE

        """
        self.state = BlockerState.INACTIVE
