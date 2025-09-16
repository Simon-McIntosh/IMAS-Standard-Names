import importlib.metadata

import pint

# ---------------------------------------------------------------------------
# Version metadata
# ---------------------------------------------------------------------------
# During test collection (editable / in-tree execution) the distribution
# metadata may not yet be built, causing importlib.metadata.version to raise
# either PackageNotFoundError or a bare KeyError (observed on Python 3.13 /
# importlib_metadata backport). We normalise all failures to a neutral
# "0.0.0" placeholder so tests do not error during collection.
try:  # pragma: no cover - trivial guard
    try:
        __version__ = importlib.metadata.version("imas-standard-names")
    except KeyError:  # metadata object exists but lacks 'Version' key
        __version__ = "0.0.0"
except importlib.metadata.PackageNotFoundError:  # distribution not installed
    __version__ = "0.0.0"

from .generic_names import GenericNames  # re-export

__all__ = ["__version__", "GenericNames"]


# ---------------------------------------------------------------------------
# Pint custom unit formatting
# ---------------------------------------------------------------------------
@pint.register_unit_format("F")
def format_unit_simple(unit, registry, **options):  # pragma: no cover - format
    """Return pint unit in fused dot-exponent UDUNITS syntax.
    ND
        Example: {'m': 1, 's': -2} -> 'm.s^-2'
    """
    return ".".join(u if p == 1 else f"{u}^{p}" for u, p in unit.items())
