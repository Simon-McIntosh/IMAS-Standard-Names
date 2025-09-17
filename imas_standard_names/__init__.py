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
    """Return pint unit in fused dot-exponent UDUNITS syntax using short symbols.

    Differences from pint's built-in formatters:
        * Enforces lexicographic ordering of symbols for determinism.
        * Uses the stored short symbols (no expansion to long names like 'meter').
        * Represents denominators with negative exponents only (no division symbol).
    """
    items = [(str(sym), int(exp)) for sym, exp in unit.items() if int(exp) != 0]
    items.sort(key=lambda x: x[0])
    return ".".join(sym if exp == 1 else f"{sym}^{exp}" for sym, exp in items)


__all__.append("format_unit_simple")
