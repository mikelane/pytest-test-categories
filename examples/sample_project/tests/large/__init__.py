"""Large tests: Full integration with real external services.

Large tests follow Google's test size guidelines:
- Complete in under 15 minutes
- May access external networks
- May use real databases and services
- May have non-deterministic behavior

Use large tests sparingly for end-to-end validation that cannot
be achieved with smaller tests.
"""

from __future__ import annotations
