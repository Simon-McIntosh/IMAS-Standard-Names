import importlib.metadata

try:  # pint is optional at import time for build hooks
    import pint  # type: ignore
except Exception:  # pragma: no cover - allow package import without pint
    pint = None  # type: ignore[assignment]

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

__all__ = ["__version__"]


# ---------------------------------------------------------------------------
# Pint custom unit formatting (register format 'F' when pint is available)
# ---------------------------------------------------------------------------

if pint is not None:

    def format_unit_udunits_dot_exponent(
        unit, registry, **options
    ):  # pragma: no cover - format
        """Return UDUNITS-style dot-exponent string using short symbols.

        This formatter is registered with pint under the short name 'F' and
        produces strings like "m.s^-2" using unit symbols with dot-separated
        factors and caret exponents.

        Parameters:
            unit: The pint UnitsContainer mapping symbols to exponents.
            registry: The pint UnitRegistry (unused but part of the protocol).
            **options: Additional formatting options (unused).

        Returns:
            A string with UDUNITS-style formatting, using short unit symbols.
        """
        items = sorted(
            ((str(sym), int(exp)) for sym, exp in unit.items() if int(exp)),
            key=lambda x: x[0],
        )
        return ".".join(sym if exp == 1 else f"{sym}^{exp}" for sym, exp in items)

    # Register with pint; do not export in package namespace
    pint.register_unit_format("F")(format_unit_udunits_dot_exponent)
