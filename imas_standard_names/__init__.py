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
# Grammar public surface
# ---------------------------------------------------------------------------

try:
    from imas_standard_names.grammar.ir import StandardNameIR
    from imas_standard_names.grammar.parser import (
        Diagnostic,
        ParseError,
        ParseResult,
        parse,
        validate_round_trip,
    )
    from imas_standard_names.grammar.render import compose
    from imas_standard_names.grammar.terms import (
        StandardTerm,
        fetch_standard_terms,
        search_standard_terms,
        standard_terms,
    )

    try:
        from imas_standard_names.grammar.context import get_grammar_context
    except ImportError:  # pragma: no cover - build-time only
        get_grammar_context = None  # type: ignore[assignment]

    __all__ = [
        *__all__,
        "Diagnostic",
        "ParseError",
        "ParseResult",
        "StandardNameIR",
        "StandardTerm",
        "compose",
        "get_grammar_context",
        "parse",
        "validate_round_trip",
        "fetch_standard_terms",
        "search_standard_terms",
        "standard_terms",
    ]
except Exception:  # pragma: no cover - defensive for code-generation stages
    pass


# ---------------------------------------------------------------------------
# Value-provenance (estimator) controlled vocabulary — link metadata, not a
# grammar segment. See imas_standard_names.value_provenance.
# ---------------------------------------------------------------------------

try:
    from imas_standard_names.value_provenance import (
        VALUE_PROVENANCE,
        ValueProvenanceTerm,
        get_value_provenance,
        is_value_provenance,
        provenance_for_dd_facet,
        value_provenance_terms,
    )

    __all__ = [
        *__all__,
        "VALUE_PROVENANCE",
        "ValueProvenanceTerm",
        "get_value_provenance",
        "is_value_provenance",
        "provenance_for_dd_facet",
        "value_provenance_terms",
    ]
except Exception:  # pragma: no cover - defensive for code-generation stages
    pass


# ---------------------------------------------------------------------------
# Pint custom unit formatting (register format 'F' when pint is available)
# ---------------------------------------------------------------------------

# ASCII spellings for the few short symbols pint renders with non-ASCII
# glyphs (ohm sign, micro prefix, degree). The catalog's authored units are
# strictly ASCII alphanumeric, so the canonical form must be too — otherwise
# a stored "m.ohm" would silently rewrite to "m.Ω" on load. Any non-ASCII
# glyph not mapped here survives into the output and is caught by the
# dot-exponent stability test rather than corrupting a stored unit.
_ASCII_UNIT_SYMBOLS = {
    "Ω": "ohm",  # Ω OHM SIGN
    "Ω": "ohm",  # Ω GREEK CAPITAL LETTER OMEGA
    "µ": "u",  # µ MICRO SIGN
    "μ": "u",  # μ GREEK SMALL LETTER MU
    "°": "deg",  # ° DEGREE SIGN (e.g. °C -> degC)
}


def _asciify_unit_symbol(sym: str) -> str:
    for glyph, ascii_name in _ASCII_UNIT_SYMBOLS.items():
        sym = sym.replace(glyph, ascii_name)
    return sym


if pint is not None:

    def format_unit_udunits_dot_exponent(unit, registry, **options):
        """Return UDUNITS-style dot-exponent string using short symbols.

        This formatter is registered with pint under the short name 'F' and
        produces strings like "m.s^-2": ASCII short symbols, sorted, with
        dot-separated factors and caret exponents. Exponents are coerced to
        ``int`` so pint's float re-parse never leaks a ``.0`` artifact, and
        pint's non-ASCII short glyphs (Ω, µ, °) are mapped to their ASCII
        spellings before sorting so the ordering authority stays byte-stable.

        Parameters:
            unit: The pint UnitsContainer mapping symbols to exponents.
            registry: The pint UnitRegistry (unused but part of the protocol).
            **options: Additional formatting options (unused).

        Returns:
            A string with UDUNITS-style formatting, using short unit symbols.
        """
        items = sorted(
            (
                (_asciify_unit_symbol(str(sym)), int(exp))
                for sym, exp in unit.items()
                if int(exp)
            ),
            key=lambda x: x[0],
        )
        return ".".join(sym if exp == 1 else f"{sym}^{exp}" for sym, exp in items)

    # Register with pint; do not export in package namespace
    pint.register_unit_format("F")(format_unit_udunits_dot_exponent)

    def canonical_unit(unit: str) -> str:
        """Return the single canonical dot-exponent form of a unit string.

        This is the one authority for unit ordering and symbol spelling.  A
        unit string is parsed through pint and formatted with the sorted
        ASCII short-symbol formatter (``~F``) so that ordering-only and
        spelling-only differences collapse to string equality: both the
        SN-side stored unit and any DD-side comparison string are normalized
        through it, and ``canonical_unit(sn) == canonical_unit(dd)`` is a
        pure string compare after normalization.

        Dimensionless is represented by the sentinel ``"1"``.  Strings pint
        cannot parse raise ``ValueError``.  Authoring conventions (no
        whitespace, no ``/`` or ``*``) are enforced by callers, not here, so
        this helper stays a lenient normalizer usable on either side of the
        comparison.
        """
        if unit == "1":
            return "1"
        try:
            parsed = pint.Unit(unit)
        except Exception as exc:  # pragma: no cover - defensive
            raise ValueError(f"Invalid unit '{unit}': {exc}") from exc
        formatted = f"{parsed:~F}"
        # A dimensionless-but-non-"1" unit (e.g. a pure angle) formats empty;
        # normalize it to the dimensionless sentinel.
        return formatted or "1"

else:  # pragma: no cover - pint-less build hook

    def canonical_unit(unit: str) -> str:
        return unit


__all__ = [*__all__, "canonical_unit"]
