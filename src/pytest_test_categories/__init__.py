"""A pytest plugin to enforce test timing constraints and size distributions.

The test limits are taken from the book Software Engineering at Google.
"""

from __future__ import annotations

from .plugin import *  # noqa: F403
from .reporting import *  # noqa: F403
