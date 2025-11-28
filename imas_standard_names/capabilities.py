"""Runtime capability detection for optional dependencies.

Detects availability of quality validation and vocabulary management tools
without importing them (avoiding hard dependencies).
"""

__all__ = ["check_write_capabilities", "get_mode_description"]


def check_write_capabilities() -> dict[str, bool]:
    """Check which write capabilities are available at runtime.

    Returns:
        Dictionary mapping capability names to availability status:
        - edit_catalog: Core editing (always True)
        - quality_validation: proselint available
        - vocabulary_management: spacy available
    """
    capabilities = {
        "edit_catalog": True,  # Always available (core functionality)
        "quality_validation": False,
        "vocabulary_management": False,
    }

    # Check proselint availability
    try:
        import proselint  # noqa: F401

        capabilities["quality_validation"] = True
    except ImportError:
        pass

    # Check spacy availability
    try:
        import spacy  # noqa: F401

        capabilities["vocabulary_management"] = True
    except ImportError:
        pass

    return capabilities


def get_mode_description(read_only: bool, capabilities: dict[str, bool]) -> str:
    """Get human-readable description of current operational mode.

    Args:
        read_only: Whether catalog is read-only
        capabilities: Capability dict from check_write_capabilities()

    Returns:
        Mode description string
    """
    if read_only:
        return "read-only"

    if all(capabilities.values()):
        return "read-write (full)"
    elif capabilities["edit_catalog"]:
        return "read-write (basic)"
    else:
        return "read-only"
