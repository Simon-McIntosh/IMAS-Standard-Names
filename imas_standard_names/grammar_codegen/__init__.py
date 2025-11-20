"""Import-light utilities for generating grammar code (types + metadata).

Prefer this package over importing from the runtime grammar package to avoid
cycles during generation.
"""

from __future__ import annotations

from .generate import main

__all__ = ["main"]
