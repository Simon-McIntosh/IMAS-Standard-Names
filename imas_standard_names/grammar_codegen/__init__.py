"""Import-light utilities for generating grammar code (types + metadata).

Prefer this package over importing from the runtime grammar package to avoid
cycles during generation.

Note:
Avoid importing the ``generate`` submodule at package import time. When running
``python -m imas_standard_names.grammar_codegen.generate``, Python first imports
the package ``imas_standard_names.grammar_codegen`` and then executes the
submodule ``generate``. If ``__init__`` imports ``generate`` eagerly, the
submodule appears in ``sys.modules`` prior to execution, which triggers a
RuntimeWarning from ``runpy``. We use a lazy re-export to prevent that warning
while preserving the convenience import ``from imas_standard_names.grammar_codegen import main``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = ["main"]

# Provide better type checking for consumers without importing at runtime
if TYPE_CHECKING:  # pragma: no cover - type-checkers only
    from .generate import main as main  # noqa: F401


def __getattr__(name: str):
    if name == "main":
        # Lazy import to avoid pre-importing the submodule during package import
        from .generate import main as _main

        return _main
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
