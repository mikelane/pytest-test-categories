"""Medium tests: May use localhost, containers, and external systems (with care).

Medium tests follow Google's test size guidelines:
- Complete in under 5 minutes
- May access localhost network (but not external networks)
- May use containers (e.g., testcontainers)
- Should minimize external system dependencies

Use @pytest.mark.medium(allow_external_systems=True) to suppress
warnings when using testcontainers or similar tools.
"""

from __future__ import annotations
