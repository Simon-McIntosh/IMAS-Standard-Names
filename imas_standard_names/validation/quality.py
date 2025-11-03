"""Quality validation checks for standard name descriptions and metadata.

Uses industry-standard NLP tools for comprehensive quality assessment:
- proselint: Writing style, redundancy, clichés, typography
- spacy: Semantic analysis, terminology consistency, NLP features
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal

from ..grammar.model_types import Component, Object, Position, Process, Subject
from ..operators import PRIMITIVE_OPERATORS

if TYPE_CHECKING:
    from ..models import StandardNameEntry

__all__ = ["run_quality_checks", "QualityLevel", "QualityChecker"]

QualityLevel = Literal["error", "warning", "info"]


class QualityChecker:
    """Comprehensive quality checker using proselint and spaCy."""

    def __init__(self):
        """Initialize quality checker with lazy-loaded backends."""
        self._proselint = None
        self._nlp = None
        self._physics_vocab = self._build_physics_vocabulary()

    @staticmethod
    def _build_physics_vocabulary() -> set[str]:
        """Build set of valid physics/fusion terminology from grammar types and catalog.

        Dynamically extracts base names from the catalog to stay in sync with actual usage.
        Uses late import to avoid circular dependency during module loading.
        """
        vocab = set()

        # Add all grammar vocabulary (segments with constrained tokens)
        for enum_class in [Component, Subject, Object, Position, Process]:
            vocab.update(member.value for member in enum_class)

        # Add primitive operators (already controlled in operators.py)
        vocab.update(PRIMITIVE_OPERATORS)

        # Add all base names from the catalog (dynamic - reflects actual usage)
        # Late import avoids circular dependency: validation -> repository -> services -> validation
        try:
            from ..grammar.model import parse_standard_name  # noqa: PLC0415
            from ..repository import StandardNameCatalog  # noqa: PLC0415

            catalog = StandardNameCatalog()
            for entry in catalog.list():
                # Extract base by parsing the standard name
                parsed = parse_standard_name(entry.name)
                vocab.add(parsed.base)
        except Exception:
            # If catalog loading fails, continue with grammar-only vocab
            pass

        return vocab

    @property
    def proselint(self):
        """Lazy-load proselint."""
        if self._proselint is None:
            from proselint.tools import lint  # noqa: PLC0415

            self._proselint = lint
        return self._proselint

    @property
    def nlp(self):
        """Lazy-load spaCy with small English model."""
        if self._nlp is None:
            try:
                import spacy  # noqa: PLC0415

                # Try to load small model, fallback to blank
                try:
                    self._nlp = spacy.load("en_core_web_sm")
                except OSError:
                    # Model not installed, use blank model with basic pipeline
                    self._nlp = spacy.blank("en")
                    if "parser" not in self._nlp.pipe_names:
                        self._nlp.add_pipe("parser")
                    if "tagger" not in self._nlp.pipe_names:
                        self._nlp.add_pipe("tagger")
            except Exception:
                self._nlp = None
        return self._nlp

    def check_proselint(self, name: str, desc: str) -> list[tuple[QualityLevel, str]]:
        """Check description with proselint for style issues."""
        issues: list[tuple[QualityLevel, str]] = []
        try:
            prose_issues = self.proselint(desc)
            for issue in prose_issues:
                # issue is (check, message, line, column, start, end, extent, severity, replacements)
                check_name = issue[0]
                message = issue[1]
                severity = issue[7]

                # Map proselint severity to our levels
                level_map: dict[str, QualityLevel] = {
                    "error": "error",
                    "warning": "warning",
                    "suggestion": "info",
                }
                level = level_map.get(severity, "info")

                # Filter to relevant checks for technical descriptions
                relevant_checks = [
                    "redundancy",
                    "repetitiveness",
                    "cliches",
                    "jargon",
                    "typography",
                    "brevity",
                    "illogic",
                ]
                if any(check in check_name for check in relevant_checks):
                    issues.append((level, f"{name}: {message} ({check_name})"))
        except Exception:
            pass  # Don't fail validation if proselint has issues

        return issues

    def check_semantic(self, name: str, desc: str) -> list[tuple[QualityLevel, str]]:
        """Check description with spaCy for semantic issues."""
        issues: list[tuple[QualityLevel, str]] = []
        if self.nlp is None:
            return issues

        try:
            doc = self.nlp(desc)

            # Check 1: Sentence structure - prefer complete sentences for longer descriptions
            if len(list(doc.sents)) == 0 and len(desc) > 30:
                issues.append(
                    ("info", f"{name}: description could be a complete sentence")
                )

            # Check 2: Validate key terms are present
            name_base = name.split("_")[-1] if "_" in name else name
            if name_base in self._physics_vocab and len(desc) > 15:
                # Extract lemmatized nouns and verbs from description
                key_tokens = {
                    token.lemma_.lower()
                    for token in doc
                    if token.pos_ in ("NOUN", "VERB", "ADJ")
                }
                if name_base not in key_tokens and name_base not in desc.lower():
                    issues.append(
                        (
                            "info",
                            f"{name}: description could reference '{name_base}' more clearly",
                        )
                    )

            # Check 3: Overly complex sentence structure
            for sent in doc.sents:
                if len(list(sent.noun_chunks)) > 4:
                    issues.append(
                        (
                            "info",
                            f"{name}: description may be too complex - consider simplifying",
                        )
                    )
                    break

            # Check 4: Passive voice detection (prefer active voice)
            has_passive = any(token.dep_ == "auxpass" for token in doc)
            if has_passive:
                issues.append(
                    ("info", f"{name}: consider active voice instead of passive")
                )

        except Exception:
            pass  # Don't fail if spaCy has issues

        return issues

    def check_domain_specific(
        self,
        name: str,
        desc: str,
        entry: StandardNameEntry,  # type: ignore[name-defined]
    ) -> list[tuple[QualityLevel, str]]:
        """Domain-specific checks for fusion physics standard names."""
        issues: list[tuple[QualityLevel, str]] = []
        desc_lower = desc.lower()

        # Check 1: Tautological descriptions
        tautology_patterns = [
            (
                r"(radial|vertical|toroidal|poloidal)\s+\w+.*\s+in\s+\1\s+direction",
                "X coordinate/position ... in X direction",
            ),
            (r"(\w+)\s+measured\s+by\s+\1", "X measured by X"),
            (r"(\w+)\s+from\s+\1\s+(diagnostic|sensor)", "X from X diagnostic"),
        ]

        for pattern, desc_pattern in tautology_patterns:
            if re.search(pattern, desc_lower):
                issues.append(("error", f"{name}: tautology - {desc_pattern}"))

        # Check 2: Deprecated '_from_' pattern for device sources
        device_terms = [
            "probe",
            "detector",
            "coil",
            "loop",
            "antenna",
            "spectrometer",
            "interferometer",
            "beam",
            "sensor",
            "diagnostic",
        ]
        if "_from_" in name:
            for term in device_terms:
                if term in name:
                    issues.append(
                        (
                            "error",
                            f"{name}: uses deprecated '_from_<device>' pattern. "
                            f"Use '<device>_<signal>' for device properties, "
                            f"or remove device from name for physics quantities.",
                        )
                    )
                    break

        # Check 3: Component descriptions should mention axis
        if "_component_of_" in name:
            axis = name.split("_component_of_")[0].split("_")[-1]
            if axis not in desc_lower:
                issues.append(
                    (
                        "warning",
                        f"{name}: component description should mention axis '{axis}'",
                    )
                )

        # Check 4: Operator descriptions should clarify transformation
        operators = [
            "gradient",
            "curl",
            "divergence",
            "time_derivative",
            "laplacian",
            "magnitude",
        ]
        for op in operators:
            if f"{op}_of_" in name and op.replace("_", " ") not in desc_lower:
                issues.append(("info", f"{name}: could clarify '{op}' operation"))

        # Check 5: Redundant name repetition
        name_parts = name.split("_")
        for i in range(len(name_parts) - 2):
            sequence = " ".join(name_parts[i : i + 3])
            if sequence in desc_lower and len(sequence) > 10:
                issues.append(("warning", f"{name}: redundantly repeats '{sequence}'"))
                break

        # Check 6: Description is just name with spaces
        if desc_lower.replace(" ", "_") == name:
            issues.append(("error", f"{name}: description merely restates the name"))

        # Check 7: Vague phrases
        vague_phrases = [
            "related to",
            "associated with",
            "regarding",
            "about",
            "concerning",
            "pertaining to",
        ]
        for phrase in vague_phrases:
            if phrase in desc_lower:
                issues.append(("warning", f"{name}: avoid vague phrase '{phrase}'"))

        return issues


# Singleton instance
_checker: QualityChecker | None = None


def get_checker() -> QualityChecker:
    """Get or create singleton quality checker instance."""
    global _checker
    if _checker is None:
        _checker = QualityChecker()
    return _checker


def run_quality_checks(
    entries: dict[str, StandardNameEntry],  # type: ignore[name-defined]
) -> list[tuple[QualityLevel, str]]:
    """Run comprehensive quality checks on standard name descriptions.

    Uses proselint for style and spaCy for semantic analysis.

    Returns:
        List of (level, message) tuples where level is 'error', 'warning', or 'info'
    """
    issues: list[tuple[QualityLevel, str]] = []
    checker = get_checker()

    for name, entry in entries.items():
        desc = entry.description.strip()

        # Basic validation
        if not desc:
            issues.append(("error", f"{name}: description is empty"))
            continue
        if len(desc) < 10:
            issues.append(
                ("warning", f"{name}: description too short ({len(desc)} chars)")
            )
        if len(desc) > 120:
            issues.append(
                ("warning", f"{name}: exceeds 120 characters ({len(desc)} chars)")
            )
        if not desc[0].isupper():
            issues.append(("info", f"{name}: should start with capital letter"))

        # Skip detailed checks for very short descriptions
        if len(desc) < 10:
            continue

        # Run all checkers
        issues.extend(checker.check_proselint(name, desc))
        issues.extend(checker.check_semantic(name, desc))
        issues.extend(checker.check_domain_specific(name, desc, entry))

    return issues


def format_quality_report(
    issues: list[tuple[QualityLevel, str]], show_level: QualityLevel | None = None
) -> str:
    """Format quality issues as a readable report.

    Args:
        issues: List of (level, message) tuples
        show_level: If specified, only show issues at this level or higher
    """
    if not issues:
        return "✓ No quality issues found"

    level_order = {"error": 0, "warning": 1, "info": 2}
    min_level = level_order.get(show_level, 2) if show_level else 2

    filtered = [
        (level, msg) for level, msg in issues if level_order.get(level, 2) <= min_level
    ]

    if not filtered:
        return "✓ No quality issues at requested level"

    lines = ["Quality Issues:", ""]
    error_count = sum(1 for level, _ in filtered if level == "error")
    warning_count = sum(1 for level, _ in filtered if level == "warning")
    info_count = sum(1 for level, _ in filtered if level == "info")

    lines.append(
        f"Summary: {error_count} errors, {warning_count} warnings, {info_count} info\n"
    )

    # Group by level
    for level_name in ["error", "warning", "info"]:
        level_issues = [msg for level, msg in filtered if level == level_name]
        if level_issues:
            symbol = {"error": "✗", "warning": "⚠", "info": "ℹ"}[level_name]
            lines.append(f"{symbol} {level_name.upper()}S:")
            for msg in level_issues:
                lines.append(f"  {msg}")
            lines.append("")

    return "\n".join(lines)
