"""Production thread monitor adapter using threading module patching.

This module provides the production implementation of ThreadMonitorPort that
actually intercepts thread creation by patching the threading module.

The ThreadPatchingMonitor follows hexagonal architecture principles:
- Implements the ThreadMonitorPort interface (port)
- Patches threading.Thread and concurrent.futures executors to intercept creation
- Emits pytest warnings on thread creation in small tests
- Restores original threading behavior on deactivation

Unlike other blockers that RAISE exceptions, this monitor WARNS because:
1. Many libraries use threading internally (logging, garbage collection)
2. Some test frameworks use threading
3. Blocking threading could break legitimate test infrastructure

Example:
    >>> monitor = ThreadPatchingMonitor()
    >>> try:
    ...     monitor.activate(TestSize.SMALL, EnforcementMode.WARN)
    ...     # Any threading.Thread() call will now emit a warning
    ... finally:
    ...     monitor.deactivate()  # Restore original threading behavior

See Also:
    - ThreadMonitorPort: The abstract interface in ports/threading.py
    - FakeThreadMonitor: Test adapter in adapters/fake_threading.py
    - SocketPatchingNetworkBlocker: Similar production adapter pattern for networking

"""

from __future__ import annotations

import concurrent.futures
import threading
import warnings

from pydantic import Field

from pytest_test_categories.ports.network import EnforcementMode
from pytest_test_categories.ports.threading import ThreadMonitorPort
from pytest_test_categories.types import TestSize


class ThreadPatchingMonitor(ThreadMonitorPort):
    """Production adapter that patches threading modules to monitor thread creation.

    This adapter intercepts thread creation by replacing threading.Thread and
    concurrent.futures executors with wrapper classes that emit warnings.

    The patching is reversible - deactivate() restores the original classes.

    Attributes:
        state: Current monitor state (inherited from ThreadMonitorPort).
        current_test_size: The test size set during activation.
        current_enforcement_mode: The enforcement mode set during activation.
        current_test_nodeid: The pytest node ID of the current test.

    Warning:
        This adapter modifies global state (threading.Thread). Always use in a
        try/finally block or context manager to ensure cleanup.

    Example:
        >>> monitor = ThreadPatchingMonitor()
        >>> try:
        ...     monitor.activate(TestSize.SMALL, EnforcementMode.WARN)
        ...     threading.Thread(target=lambda: None)  # Emits warning
        ... finally:
        ...     monitor.deactivate()

    """

    current_test_size: TestSize | None = Field(default=None, description='Test size')
    current_enforcement_mode: EnforcementMode | None = Field(default=None, description='Enforcement mode')
    current_test_nodeid: str = Field(default='', description='Test node ID')

    def model_post_init(self, context: object, /) -> None:  # noqa: ARG002
        """Initialize post-Pydantic setup, storing reference to original classes."""
        object.__setattr__(self, '_original_thread_class', None)
        object.__setattr__(self, '_original_thread_pool_executor', None)
        object.__setattr__(self, '_original_process_pool_executor', None)

    @property
    def is_monitoring(self) -> bool:
        """Return True if actively monitoring for thread creation.

        Only small tests are monitored for threading usage.

        Returns:
            True if monitoring is active and test is SMALL, False otherwise.

        """
        return self.current_test_size == TestSize.SMALL

    def _do_activate(self, test_size: TestSize, enforcement_mode: EnforcementMode) -> None:
        """Install threading wrappers to intercept thread creation.

        Installs wrapper classes for:
        - threading.Thread (Timer inherits from Thread so is covered)
        - concurrent.futures.ThreadPoolExecutor
        - concurrent.futures.ProcessPoolExecutor

        Note: We don't patch Timer separately because it inherits from Thread.
        When Thread is patched, Timer.__init__() calls Thread.__init__() which
        will trigger our monitoring.

        Args:
            test_size: The size category of the current test.
            enforcement_mode: How to handle detections.

        """
        self.current_test_size = test_size
        self.current_enforcement_mode = enforcement_mode

        object.__setattr__(self, '_original_thread_class', threading.Thread)
        object.__setattr__(self, '_original_thread_pool_executor', concurrent.futures.ThreadPoolExecutor)
        object.__setattr__(self, '_original_process_pool_executor', concurrent.futures.ProcessPoolExecutor)

        threading.Thread = self._create_patched_thread_class()  # type: ignore[misc,assignment]
        concurrent.futures.ThreadPoolExecutor = self._create_patched_thread_pool_executor()  # type: ignore[misc,assignment]
        concurrent.futures.ProcessPoolExecutor = self._create_patched_process_pool_executor()  # type: ignore[misc,assignment]

    def _do_deactivate(self) -> None:
        """Restore the original threading classes.

        Restores all original classes that were saved during activation.

        """
        original_thread = object.__getattribute__(self, '_original_thread_class')
        if original_thread is not None:
            threading.Thread = original_thread  # type: ignore[misc]

        original_executor = object.__getattribute__(self, '_original_thread_pool_executor')
        if original_executor is not None:
            concurrent.futures.ThreadPoolExecutor = original_executor  # type: ignore[misc]

        original_process_executor = object.__getattribute__(self, '_original_process_pool_executor')
        if original_process_executor is not None:
            concurrent.futures.ProcessPoolExecutor = original_process_executor  # type: ignore[misc]

    def _do_on_thread_creation(self, thread_type: str, test_nodeid: str) -> None:
        """Emit a pytest warning for thread creation in small tests.

        Args:
            thread_type: The type of thread being created.
            test_nodeid: The pytest node ID of the test creating the thread.

        """
        if self.current_test_size == TestSize.SMALL and self.current_enforcement_mode == EnforcementMode.WARN:
            warning_msg = (
                f"Small test '{test_nodeid}' uses {thread_type}. "
                f'Small tests should be single-threaded for determinism. '
                f'Consider using @pytest.mark.medium if concurrency testing is required.'
            )
            warnings.warn(warning_msg, stacklevel=4)

    def reset(self) -> None:
        """Reset monitor to initial state, restoring original threading classes.

        This is safe to call regardless of current state.

        """
        original_thread = object.__getattribute__(self, '_original_thread_class')
        if original_thread is not None:
            threading.Thread = original_thread  # type: ignore[misc]
            object.__setattr__(self, '_original_thread_class', None)

        original_executor = object.__getattribute__(self, '_original_thread_pool_executor')
        if original_executor is not None:
            concurrent.futures.ThreadPoolExecutor = original_executor  # type: ignore[misc]
            object.__setattr__(self, '_original_thread_pool_executor', None)

        original_process_executor = object.__getattribute__(self, '_original_process_pool_executor')
        if original_process_executor is not None:
            concurrent.futures.ProcessPoolExecutor = original_process_executor  # type: ignore[misc]
            object.__setattr__(self, '_original_process_pool_executor', None)

        super().reset()
        self.current_test_size = None
        self.current_enforcement_mode = None
        self.current_test_nodeid = ''

    def _create_patched_thread_class(self) -> type:
        """Create a Thread class that emits warnings on creation.

        Returns:
            A Thread subclass that monitors creation for small tests.

        Note:
            We use original_thread.__init__(self, ...) instead of super().__init__()
            because Timer calls Thread.__init__(self) where self is a Timer instance.
            Using super() without arguments would fail because the implicit class
            (MonitoringThread) doesn't match the instance (Timer).

        """
        monitor = self
        original_thread = object.__getattribute__(self, '_original_thread_class')

        class MonitoringThread(original_thread):  # type: ignore[valid-type,misc]
            """Thread wrapper that emits warnings for small tests."""

            def __init__(self, *args: object, **kwargs: object) -> None:
                """Initialize thread and emit warning if monitoring small tests."""
                if monitor.is_monitoring:
                    monitor._do_on_thread_creation('threading.Thread', monitor.current_test_nodeid)  # noqa: SLF001
                original_thread.__init__(self, *args, **kwargs)

        return MonitoringThread

    def _create_patched_thread_pool_executor(self) -> type:
        """Create a ThreadPoolExecutor class that emits warnings on creation.

        Returns:
            A ThreadPoolExecutor subclass that monitors creation for small tests.

        """
        monitor = self
        original_executor = object.__getattribute__(self, '_original_thread_pool_executor')

        class MonitoringThreadPoolExecutor(original_executor):  # type: ignore[valid-type,misc]
            """ThreadPoolExecutor wrapper that emits warnings for small tests."""

            def __init__(self, *args: object, **kwargs: object) -> None:
                """Initialize executor and emit warning if monitoring small tests."""
                if monitor.is_monitoring:
                    monitor._do_on_thread_creation(  # noqa: SLF001
                        'concurrent.futures.ThreadPoolExecutor', monitor.current_test_nodeid
                    )
                super().__init__(*args, **kwargs)

        return MonitoringThreadPoolExecutor

    def _create_patched_process_pool_executor(self) -> type:
        """Create a ProcessPoolExecutor class that emits warnings on creation.

        Returns:
            A ProcessPoolExecutor subclass that monitors creation for small tests.

        """
        monitor = self
        original_executor = object.__getattribute__(self, '_original_process_pool_executor')

        class MonitoringProcessPoolExecutor(original_executor):  # type: ignore[valid-type,misc]
            """ProcessPoolExecutor wrapper that emits warnings for small tests."""

            def __init__(self, *args: object, **kwargs: object) -> None:
                """Initialize executor and emit warning if monitoring small tests."""
                if monitor.is_monitoring:
                    monitor._do_on_thread_creation(  # noqa: SLF001
                        'concurrent.futures.ProcessPoolExecutor', monitor.current_test_nodeid
                    )
                super().__init__(*args, **kwargs)

        return MonitoringProcessPoolExecutor
