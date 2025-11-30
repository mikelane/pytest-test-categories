"""Small tests: Fast, hermetic, no external dependencies.

Small tests follow Google's test size guidelines:
- Complete in under 1 second
- No network access
- No filesystem access (except tmp_path)
- No subprocess spawning
- No database connections
- Use mocks and fakes for external dependencies

The pytest-test-categories plugin enforces these constraints
when enforcement mode is enabled.
"""

from __future__ import annotations
