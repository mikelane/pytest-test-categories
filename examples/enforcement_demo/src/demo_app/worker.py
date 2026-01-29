"""Background worker demonstrating threading dependency patterns.

This module shows background job processing with threads. Tests for
threaded code often become flaky because they:
- Use time.sleep() to wait for threads
- Have race conditions between setup and assertion
- Are sensitive to timing variations
- Can hang indefinitely if threads don't complete

Solutions:
1. Test the work logic synchronously (without threading)
2. Use proper synchronization (Event, Condition, Queue)
3. Use medium tests for actual threading integration
4. Mock threading constructs for unit tests
"""

from __future__ import annotations

import queue
import threading
import time
from collections.abc import Callable
from dataclasses import (
    dataclass,
    field,
)
from typing import (
    Any,
)


@dataclass
class Job:
    """A job to be processed by the worker."""

    id: str
    payload: dict[str, Any]
    status: str = "pending"
    result: Any = None
    error: str | None = None


def process_job(job: Job) -> Job:
    """Process a single job synchronously.

    This is the core logic that should be tested in small tests.
    It doesn't involve any threading.

    Args:
        job: The job to process.

    Returns:
        The processed job with updated status.

    """
    try:
        # Simulate some processing based on payload
        if "error" in job.payload:
            raise ValueError(job.payload["error"])  # noqa: TRY301

        result = {"processed": True, "input": job.payload}
        job.result = result
        job.status = "completed"
    except Exception as e:  # noqa: BLE001
        job.status = "failed"
        job.error = str(e)

    return job


@dataclass
class BackgroundWorker:
    """Background worker that processes jobs in a separate thread.

    This worker uses a queue for job submission and processes jobs
    in the background. The threading aspect should be tested in
    medium tests, while the job processing logic should be tested
    in small tests.
    """

    process_func: Callable[[Job], Job] = field(default_factory=lambda: process_job)
    _queue: queue.Queue[Job | None] = field(default_factory=queue.Queue)
    _thread: threading.Thread | None = None
    _running: bool = False
    _processed_jobs: list[Job] = field(default_factory=list)
    _completed_event: threading.Event = field(default_factory=threading.Event)

    def start(self) -> None:
        """Start the background worker thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the worker and wait for completion.

        Args:
            timeout: Maximum time to wait for the thread to stop.

        """
        if not self._running:
            return

        self._running = False
        self._queue.put(None)  # Sentinel to unblock the queue

        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def submit(self, job: Job) -> None:
        """Submit a job for background processing.

        Args:
            job: The job to process.

        """
        self._queue.put(job)

    def wait_for_completion(self, timeout: float | None = None) -> bool:
        """Wait for all submitted jobs to complete.

        Args:
            timeout: Maximum time to wait.

        Returns:
            True if all jobs completed, False if timeout occurred.

        """
        return self._completed_event.wait(timeout=timeout)

    @property
    def processed_jobs(self) -> list[Job]:
        """Get list of processed jobs."""
        return list(self._processed_jobs)

    def _run(self) -> None:
        """Main worker loop - runs in background thread."""
        while self._running:
            try:
                job = self._queue.get(timeout=0.1)
                if job is None:  # Sentinel value
                    break
                self.process_func(job)
                self._processed_jobs.append(job)
                self._completed_event.set()
            except queue.Empty:
                continue


def wait_for_worker(seconds: float) -> None:
    """Wait for worker to process jobs.

    This is the WRONG way to test workers - it wastes time and is flaky.
    It's here only to demonstrate the anti-pattern.

    Args:
        seconds: Number of seconds to wait.

    """
    time.sleep(seconds)
