"""Legacy loader module retained temporarily.

The repository / UnitOfWork API supersedes this module. For new code use:

    from imas_standard_names.repositories import YamlStandardNameRepository

This stub remains only so existing imports fail fast with a clear message if used.
"""

from __future__ import annotations

raise ImportError(
    "imas_standard_names.storage.loader is deprecated. Use YamlStandardNameRepository instead."
)
