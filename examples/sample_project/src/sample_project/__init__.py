"""Sample project demonstrating pytest-test-categories best practices.

This project shows how to categorize tests according to Google's "Software
Engineering at Google" test size definitions:

- Small tests: Fast, hermetic, no external dependencies
- Medium tests: May use localhost network, external systems with care
- Large tests: Full integration, may use external services
"""

from __future__ import annotations

__version__ = "0.1.0"
