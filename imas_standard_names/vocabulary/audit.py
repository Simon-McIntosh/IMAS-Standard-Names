"""Vocabulary audit logic for detecting missing tokens.

Pattern-based extraction: Analyzes raw standard name strings using regex patterns
and spaCy NLP to identify recurring tokens BEFORE parsing. This avoids the chicken-and-egg
problem where the parser can't extract tokens it doesn't know about.

Uses grammar.types enums (Component, Subject, GeometricBase, Object, Position, Process)
generated from vocabulary YAML files. After adding tokens via VocabularyEditor,
must run codegen and restart server for new tokens to be recognized.

Supports all canonical grammar segments:
- components: Directional/coordinate components (radial, toroidal, poloidal)
- subjects: Particle species (electron, ion, neutron)
- geometric_bases: Spatial quantities (position, vertex, centroid)
- objects: Physical hardware (flux_loop, antenna, coil)
- positions: Spatial locations (magnetic_axis, separatrix, midplane)
- processes: Physical mechanisms (collisions, turbulence, transport)

Pattern extraction strategies:
1. Components: Regex `^([a-z_]+)_component_of_` prefix pattern
2. Positions: Regex `_at_([a-z_]+)` suffix pattern
3. Processes: Regex `_due_to_([a-z_]+)` suffix pattern
4. Geometry/Objects: Regex `_of_([a-z_]+)` + spaCy classification (location vs equipment)
5. Subjects: spaCy POS tagging for domain nouns in subject position
6. Device: Device prefix detection before signal bases
7. Geometric bases: Token matching against controlled vocabulary
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import TYPE_CHECKING, Literal

from imas_standard_names.grammar.model import parse_standard_name
from imas_standard_names.grammar.model_types import (
    Component,
    GeometricBase,
    Object,
    Position,
    Process,
    Subject,
)
from imas_standard_names.vocabulary.vocab_models import (
    AuditResult,
    CheckResult,
    MissingToken,
)

if TYPE_CHECKING:
    from imas_standard_names.repository import StandardNameCatalog


class VocabularyAuditor:
    """Analyzes catalog for missing vocabulary tokens using pattern-based extraction.

    Uses hybrid regex + spaCy approach:
    - Regex for structured patterns (_at_X, _of_X, _due_to_X, X_component_of_)
    - spaCy for ambiguous cases (subjects, object/geometry disambiguation)
    """

    def __init__(self, repository: StandardNameCatalog):
        self.repository = repository
        self._nlp = None  # Lazy-load spaCy
        self._pattern_cache: dict[str, dict[str, int]] | None = (
            None  # Cache for _collect_patterns
        )

    @property
    def nlp(self):
        """Lazy-load spaCy with small English model."""
        if self._nlp is None:
            try:
                import spacy  # noqa: PLC0415

                try:
                    self._nlp = spacy.load("en_core_web_sm")
                except OSError:
                    # Model not installed, use blank model
                    self._nlp = spacy.blank("en")
                    if "tagger" not in self._nlp.pipe_names:
                        self._nlp.add_pipe("tagger")
            except Exception:
                self._nlp = None
        return self._nlp

    def preload_spacy(self) -> None:
        """Eagerly load spaCy model at startup to avoid first-call latency."""
        _ = self.nlp  # Trigger lazy load

    def invalidate_cache(self) -> None:
        """Invalidate pattern cache when catalog changes."""
        self._pattern_cache = None

    def audit(
        self,
        vocabulary: str | None = None,
        frequency_threshold: int = 3,
        max_results: int | None = 20,
    ) -> AuditResult:
        """
        Audit catalog for missing vocabulary tokens.

        Args:
            vocabulary: Which vocabulary to analyze (geometry, object, position, or None for all)
            frequency_threshold: Minimum occurrences to report as missing
            max_results: Maximum results per vocabulary (None for all)

        Returns:
            AuditResult with missing tokens grouped by priority:
            - high: ≥10 occurrences (immediate action recommended)
            - medium: 5-9 occurrences (should be addressed)
            - low: 3-4 occurrences (consider adding)
        """
        # Normalize scope parameter
        scope = vocabulary if vocabulary else "all"

        # Get all standard names
        all_names = self.repository.list_names()

        # Analyze each name
        patterns = self._collect_patterns(all_names)

        # Get current vocabularies
        current_vocabs = self._get_current_vocabularies()

        # Identify missing tokens
        missing = self._identify_missing(
            patterns, current_vocabs, frequency_threshold, scope, max_results
        )

        # Group by priority
        grouped_by_priority = self._group_by_priority(missing)

        # Build enhanced summary with clear labels
        summary: dict[str, int | dict[str, int]] = {
            "total_missing_tokens": sum(
                len(tokens) for tokens in missing.values() if isinstance(tokens, list)
            ),
            "by_vocabulary": {
                vocab: len(tokens)
                for vocab, tokens in missing.items()
                if tokens  # Only include vocabularies with missing tokens
            },
            "by_priority": {
                "high": len(grouped_by_priority.get("high", [])),
                "medium": len(grouped_by_priority.get("medium", [])),
                "low": len(grouped_by_priority.get("low", [])),
            },
        }

        return AuditResult(
            action="audit",
            summary=summary,
            recommendations=grouped_by_priority,
        )

    def check_name(self, name: str, frequency_threshold: int = 3) -> CheckResult:
        """
        Check if specific name would benefit from vocabulary update.

        Analyzes the name for missing tokens by:
        1. Checking parsed segments for missing vocabulary tokens
        2. Analyzing raw name string for potential missing tokens (even if parser
           couldn't recognize them due to vocabulary gaps)

        Args:
            name: Name to check
            frequency_threshold: Minimum occurrences to report as gap (default: 3)

        Returns:
            CheckResult with current parse and gap details if found
        """
        # Parse the name
        parsed = parse_standard_name(name)
        current_parse = parsed.model_dump() if hasattr(parsed, "model_dump") else {}

        # Get all patterns from catalog
        all_names = self.repository.list_names()
        patterns = self._collect_patterns(all_names)
        current_vocabs = self._get_current_vocabularies()
        min_frequency = frequency_threshold

        # First check parsed segments for missing tokens
        segment_to_vocab = {
            "component": "components",
            "coordinate": "components",
            "subject": "subjects",
            "geometric_base": "geometric_bases",
            "device": "objects",
            "object": "objects",
            "geometry": "positions",
            "position": "positions",
            "process": "processes",
        }

        for segment_name, vocab_name in segment_to_vocab.items():
            segment_val = current_parse.get(segment_name)
            if segment_val:
                # model_dump() already serialized enum to string
                token = segment_val

                # Check if token exists in vocabulary
                if token not in current_vocabs[vocab_name]:
                    # Check if it's frequent enough in catalog to suggest adding
                    if (
                        token in patterns[vocab_name]
                        and patterns[vocab_name][token] >= min_frequency
                    ):
                        affected = list(self._get_affected_names(all_names, token))
                        gap = MissingToken(
                            token=token,
                            frequency=len(affected),
                            addition_priority=self._classify_evidence(len(affected)),
                            affected_names=affected,
                            recommendation=f"Add '{token}' to {vocab_name} vocabulary",
                        )
                        return CheckResult(
                            action="check",
                            name=name,
                            current_parse=current_parse,
                            has_vocabulary_gap=True,
                            gap_details=gap,
                        )

        # Also check raw name string for potential missing tokens
        # that parser couldn't recognize due to vocabulary gaps
        raw_analysis = self._analyze_raw_name(
            name, patterns, current_vocabs, min_frequency, all_names
        )
        if raw_analysis:
            return CheckResult(
                action="check",
                name=name,
                current_parse=current_parse,
                has_vocabulary_gap=True,
                gap_details=raw_analysis,
            )

        # No gaps found
        return CheckResult(
            action="check",
            name=name,
            current_parse=current_parse,
            has_vocabulary_gap=False,
            gap_details=None,
        )

    def _analyze_raw_name(
        self,
        name: str,
        patterns: dict[str, dict[str, int]],
        current_vocabs: dict[str, set[str]],
        min_frequency: int,
        all_names: list[str],
    ) -> MissingToken | None:
        """
        Analyze raw name string for potential missing tokens.

        Uses pattern matching to detect tokens that should be in vocabulary
        but aren't recognized by parser yet.
        """
        # Check for _of_ pattern (could be object/geometry/position)
        of_matches = re.findall(r"_of_([a-z][a-z0-9_]+)", name)
        for token in of_matches:
            if self._is_valid_token(token):
                # Check if it's a frequent missing token in positions vocabulary
                if (
                    token in patterns["positions"]
                    and token not in current_vocabs["positions"]
                    and patterns["positions"][token] >= min_frequency
                ):
                    affected = list(self._get_affected_names(all_names, token))
                    return MissingToken(
                        token=token,
                        frequency=len(affected),
                        addition_priority=self._classify_evidence(len(affected)),
                        affected_names=affected,
                        recommendation=f"Add '{token}' to positions vocabulary",
                    )

                # Check if it's a frequent missing token in objects vocabulary
                if (
                    token in patterns["objects"]
                    and token not in current_vocabs["objects"]
                    and patterns["objects"][token] >= min_frequency
                ):
                    affected = list(self._get_affected_names(all_names, token))
                    return MissingToken(
                        token=token,
                        frequency=len(affected),
                        addition_priority=self._classify_evidence(len(affected)),
                        affected_names=affected,
                        recommendation=f"Add '{token}' to objects vocabulary",
                    )

        # Check for _at_ pattern (position)
        at_matches = re.findall(r"_at_([a-z][a-z0-9_]+)", name)
        for token in at_matches:
            if (
                self._is_valid_token(token)
                and token in patterns["positions"]
                and token not in current_vocabs["positions"]
                and patterns["positions"][token] >= min_frequency
            ):
                affected = list(self._get_affected_names(all_names, token))
                return MissingToken(
                    token=token,
                    frequency=len(affected),
                    addition_priority=self._classify_evidence(len(affected)),
                    affected_names=affected,
                    recommendation=f"Add '{token}' to positions vocabulary",
                )

        return None

    def _extract_pattern_candidates(
        self, names: list[str]
    ) -> dict[str, dict[str, int]]:
        """
        Extract vocabulary token candidates from raw name strings using pattern matching.

        This method analyzes raw strings BEFORE parsing to avoid cases
        where the parser can't extract tokens it doesn't know about.

        Uses hybrid approach:
        - Regex for clear structured patterns (90% of cases)
        - spaCy for ambiguous cases (subject detection, object/geometry disambiguation)

        Returns:
            Dict mapping vocabulary name to token frequency counts
        """
        candidates: dict[str, dict[str, int]] = {
            "components": defaultdict(int),
            "subjects": defaultdict(int),
            "geometric_bases": defaultdict(int),
            "objects": defaultdict(int),
            "positions": defaultdict(int),
            "processes": defaultdict(int),
        }

        for name in names:
            # Strategy 1: Component pattern - X_component_of_
            component_match = re.match(r"^([a-z][a-z0-9_]*)_component_of_", name)
            if component_match:
                token = component_match.group(1)
                if self._is_valid_token(token):
                    candidates["components"][token] += 1

            # Strategy 2: Position pattern - _at_X
            for match in re.finditer(r"_at_([a-z][a-z0-9_]*)", name):
                token = match.group(1)
                if self._is_valid_token(token):
                    candidates["positions"][token] += 1

            # Strategy 3: Process pattern - _due_to_X
            for match in re.finditer(r"_due_to_([a-z][a-z0-9_]*)", name):
                token = match.group(1)
                if self._is_valid_token(token):
                    candidates["processes"][token] += 1

            # Strategy 4 & 5: Geometry/Object pattern - _of_X (needs disambiguation)
            # Match COMPLETE compound tokens (greedy until end or next template keyword)
            # Stop at: _at_, _due_to_, or end of string
            for match in re.finditer(
                r"_of_([a-z][a-z0-9_]+?)(?=_at_|_due_to_|$)", name
            ):
                token = match.group(1)
                if self._is_valid_token(token):
                    # Use spaCy to classify if available
                    vocab_type = self._classify_of_token(token)
                    candidates[vocab_type][token] += 1

            # Strategy 4b: Also check for geometry tokens at start of compound names
            # Pattern: flux_surface_averaged_..., flux_surface_volume_...
            # Extract potential geometry prefix before _averaged, _area, _volume, etc.
            # Must be a compound token (contains underscore)
            prefix_match = re.match(
                r"^([a-z][a-z0-9_]+?[_][a-z0-9_]+)_(averaged|area|volume|derivative)",
                name,
            )
            if prefix_match:
                token = prefix_match.group(1)
                if self._is_valid_token(token) and "_" in token:
                    vocab_type = self._classify_of_token(token)
                    candidates[vocab_type][token] += 1

            # Strategy 6: Subject detection (requires spaCy POS tagging)
            # Extract potential subject tokens (nouns in subject position)
            subject_candidates = self._extract_subject_candidates(name)
            for token in subject_candidates:
                if self._is_valid_token(token):
                    candidates["subjects"][token] += 1

            # Strategy 7: Geometric base detection (controlled vocabulary patterns)
            # Check if name starts with known geometric base patterns
            geometric_candidates = self._extract_geometric_base_candidates(name)
            for token in geometric_candidates:
                if self._is_valid_token(token):
                    candidates["geometric_bases"][token] += 1

        return candidates

    def _is_valid_token(self, token: str) -> bool:
        """Validate token format: ^[a-z][a-z0-9_]*[a-z0-9]$|^[a-z]$"""
        if not token:
            return False
        # Single letter
        if len(token) == 1:
            return token.isalpha() and token.islower()
        # Multi-char: starts with letter, ends with letter/digit, no double underscores
        if not (token[0].isalpha() and token[0].islower()):
            return False
        if not (token[-1].isalnum() and token[-1].islower()):
            return False
        if "__" in token:
            return False
        # Check all chars are lowercase alphanumeric or underscore
        return all(c.isalnum() or c == "_" for c in token) and token.islower()

    def _classify_of_token(self, token: str) -> Literal["positions", "objects"]:
        """
        Classify _of_X token as geometry (positions) or object using spaCy.

        Uses semantic analysis:
        - Spatial/location/geometric terms → positions (geometry vocabulary)
        - Diagnostic/actuator/hardware terms → objects
        - Noun phrase chunking for compound token detection
        """
        if self.nlp is None:
            # Fallback: Enhanced heuristics without spaCy
            spatial_keywords = {
                "surface",
                "boundary",
                "axis",
                "center",
                "edge",
                "region",
                "layer",
                "zone",
                "point",
                "line",
                "plane",
                "midplane",
                "target",
                "separatrix",
                "limiter",
                "divertor",
                "wall",
            }
            equipment_keywords = {
                "loop",
                "coil",
                "antenna",
                "diagnostic",
                "sensor",
                "probe",
                "detector",
                "injector",
                "heating",
                "camera",
                "spectrometer",
                "bolometer",
                "interferometer",
                "reflectometer",
                "tile",
                "isotope",
                "species",
                "particle",
            }

            # Check for spatial keywords (prioritize longer matches)
            for keyword in spatial_keywords:
                if keyword in token:
                    return "positions"

            # Check for equipment keywords
            for keyword in equipment_keywords:
                if keyword in token:
                    return "objects"

            # Default to objects (safer default - properties are more common)
            return "objects"

        # Use spaCy for semantic classification
        doc = self.nlp(token.replace("_", " "))

        # Extract noun chunks for compound analysis
        chunks = list(doc.noun_chunks)

        # Analyze lemmas and semantic categories
        spatial_lemmas = {
            "surface",
            "boundary",
            "axis",
            "region",
            "center",
            "edge",
            "point",
            "line",
            "plane",
            "midplane",
            "location",
            "position",
            "target",
            "separatrix",
            "limiter",
            "divertor",
            "wall",
        }
        equipment_lemmas = {
            "loop",
            "coil",
            "antenna",
            "probe",
            "detector",
            "sensor",
            "diagnostic",
            "injector",
            "heating",
            "camera",
            "spectrometer",
            "bolometer",
            "interferometer",
            "reflectometer",
            "tile",
            "system",
            "isotope",
            "species",
            "particle",
        }

        # Check all tokens for semantic classification
        for tok in doc:
            if tok.pos_ in ["PROPN", "NOUN"]:
                lemma = tok.lemma_.lower()

                # Spatial/geometric terms
                if lemma in spatial_lemmas:
                    return "positions"

                # Equipment/diagnostic terms
                if lemma in equipment_lemmas:
                    return "objects"

        # Check for compound patterns (e.g., "flux surface" → geometric location)
        if len(chunks) > 0:
            # Multi-word compounds often indicate geometric features
            if len(token.split("_")) >= 2:
                # Check if compound contains spatial indicators
                for spatial in spatial_lemmas:
                    if spatial in token:
                        return "positions"

        # Default to objects (properties OF things more common than AT things)
        return "objects"

    def _extract_subject_candidates(self, name: str) -> list[str]:
        """
        Extract potential subject tokens using semantic particle detection.

        Subjects are particle species or plasma populations:
        - Single species: electron, ion, deuterium, tritium, helium, neutron
        - Compound species: fast_ion, runaway_electron, impurity_species

        Uses grammar structure: subjects appear before physical_base,
        after component/coordinate if present.
        """
        candidates = []
        parts = name.split("_")

        if len(parts) < 2:
            return candidates

        # Known particle species patterns (semantic matching)
        particle_indicators = {
            "electron",
            "ion",
            "deuterium",
            "tritium",
            "helium",
            "impurity",
            "neutral",
            "neutron",
            "proton",
            "alpha",
        }

        # Compound particle patterns
        compound_patterns = [
            ("fast", "ion"),
            ("runaway", "electron"),
            ("thermal", "ion"),
            ("suprathermal", "electron"),
        ]

        # Skip component/coordinate prefix if present
        start_idx = 0
        if len(parts) > 2 and parts[1] == "component" and parts[2] == "of":
            start_idx = 3
        elif parts[0] in {
            "radial",
            "toroidal",
            "vertical",
            "poloidal",
            "parallel",
            "normal",
            "tangential",
            "x",
            "y",
            "z",
        }:
            start_idx = 1

        # Check for compound species (fast_ion, runaway_electron)
        if start_idx + 1 < len(parts):
            compound = f"{parts[start_idx]}_{parts[start_idx + 1]}"
            if (parts[start_idx], parts[start_idx + 1]) in compound_patterns:
                candidates.append(compound)
                return candidates

        # Check for single-word species
        for i in range(start_idx, min(start_idx + 3, len(parts))):
            part = parts[i]

            # Direct pattern match
            if part in particle_indicators:
                candidates.append(part)
                continue

            # Use spaCy for semantic analysis if available
            if self.nlp and len(part) > 2:
                doc = self.nlp(part)
                for tok in doc:
                    # Check if it's a noun that matches particle patterns
                    if tok.pos_ in ["NOUN", "PROPN"]:
                        lemma = tok.lemma_.lower()
                        if lemma in particle_indicators:
                            candidates.append(part)
                            break

        return candidates

    def _extract_geometric_base_candidates(self, name: str) -> list[str]:
        """
        Extract potential geometric_base tokens.

        Geometric bases are spatial quantities like position, vertex, centroid, etc.
        They typically appear at the start of geometric names.
        """
        candidates = []

        # Common geometric base patterns
        geometric_patterns = [
            r"^(position)_",
            r"^(vertex)_",
            r"^(centroid)_",
            r"^(center)_",
            r"^(radius)_",
            r"^(distance)_",
            r"^(extent)_",
            r"^(coordinate)_",
            r"^(location)_",
            r"^(point)_",
        ]

        for pattern in geometric_patterns:
            match = re.match(pattern, name)
            if match:
                candidates.append(match.group(1))

        return candidates

    def _collect_patterns(self, names: list[str]) -> dict[str, dict[str, int]]:
        """
        Collect vocabulary token candidates from standard names.

        New implementation: Uses pattern-based extraction from raw strings to avoid
        parser dependency (chicken-and-egg problem). Falls back to parsed results
        for validation and cross-checking.

        Returns dict mapping vocabulary name to token counts.

        Results are cached for performance - invalidate cache if catalog changes.
        """
        # Return cached result if available
        if self._pattern_cache is not None:
            return self._pattern_cache

        # Primary: Pattern-based extraction from raw strings
        patterns = self._extract_pattern_candidates(names)

        # Secondary: Validate with parsed results for tokens parser can recognize
        # This catches tokens that are already in vocabulary
        for name in names:
            try:
                parsed = parse_standard_name(name)
                parse_dict = (
                    parsed.model_dump() if hasattr(parsed, "model_dump") else {}
                )

                # Check component/coordinate segment
                component_val = parse_dict.get("component")
                if component_val:
                    patterns["components"][component_val] += 1

                coordinate_val = parse_dict.get("coordinate")
                if coordinate_val:
                    patterns["components"][coordinate_val] += 1

                # Check subject segment
                subject_val = parse_dict.get("subject")
                if subject_val:
                    patterns["subjects"][subject_val] += 1

                # Check geometric_base segment
                geometric_base_val = parse_dict.get("geometric_base")
                if geometric_base_val:
                    patterns["geometric_bases"][geometric_base_val] += 1

                # Check object/device segments
                object_val = parse_dict.get("object")
                if object_val:
                    patterns["objects"][object_val] += 1

                device_val = parse_dict.get("device")
                if device_val:
                    patterns["objects"][device_val] += 1

                # Check geometry/position segments
                geometry_val = parse_dict.get("geometry")
                if geometry_val:
                    patterns["positions"][geometry_val] += 1

                position_val = parse_dict.get("position")
                if position_val:
                    patterns["positions"][position_val] += 1

                # Check process segment
                process_val = parse_dict.get("process")
                if process_val:
                    patterns["processes"][process_val] += 1

            except Exception:
                # Parser failed, rely on pattern extraction only
                continue

        # Cache the result before returning
        self._pattern_cache = patterns
        return patterns

    def _get_current_vocabularies(self) -> dict[str, set[str]]:
        """Get current vocabulary tokens from grammar.types enums.

        Accesses all grammar enums generated by codegen from vocabulary YAML files:
        - Component enum from components.yml
        - Subject enum from subjects.yml
        - GeometricBase enum from geometric_bases.yml
        - Object enum from objects.yml
        - Position enum from positions.yml
        - Process enum from processes.yml
        """
        return {
            "components": {member.value for member in Component},
            "subjects": {member.value for member in Subject},
            "geometric_bases": {member.value for member in GeometricBase},
            "objects": {member.value for member in Object},
            "positions": {member.value for member in Position},
            "processes": {member.value for member in Process},
        }

    def _identify_missing(
        self,
        patterns: dict[str, dict[str, int]],
        current_vocabs: dict[str, set[str]],
        min_frequency: int,
        scope: str,
        max_results: int | None = None,
    ) -> dict[str, list[MissingToken]]:
        """Identify tokens that appear frequently but aren't in vocabulary.

        Now checks all 6 vocabulary types: components, subjects, geometric_bases,
        objects, positions, processes.
        """
        all_vocab_types = [
            "components",
            "subjects",
            "geometric_bases",
            "objects",
            "positions",
            "processes",
        ]

        missing: dict[str, list[MissingToken]] = {
            vocab: [] for vocab in all_vocab_types
        }

        vocab_types = [scope] if scope != "all" else all_vocab_types

        for vocab_type in vocab_types:
            for token, count in patterns[vocab_type].items():
                if count >= min_frequency and token not in current_vocabs[vocab_type]:
                    all_names = self.repository.list_names()
                    affected = list(self._get_affected_names(all_names, token))
                    actual_frequency = len(affected)

                    missing[vocab_type].append(
                        MissingToken(
                            token=token,
                            frequency=actual_frequency,
                            addition_priority=self._classify_evidence(actual_frequency),
                            affected_names=affected,
                            recommendation=f"Add '{token}' to {vocab_type} vocabulary ({actual_frequency} occurrences)",
                        )
                    )

            # Sort by frequency descending and limit to max_results
            missing[vocab_type].sort(key=lambda x: x.frequency, reverse=True)
            if max_results is not None:
                missing[vocab_type] = missing[vocab_type][:max_results]

        return missing

    def _group_by_priority(
        self, missing_tokens: dict[str, list[MissingToken]]
    ) -> dict[str, list[MissingToken]]:
        """Group missing tokens by priority level."""
        grouped: dict[str, list[MissingToken]] = {
            "high": [],
            "medium": [],
            "low": [],
        }

        for vocab_tokens in missing_tokens.values():
            for token_info in vocab_tokens:
                quality = token_info.addition_priority
                if quality in grouped:
                    grouped[quality].append(token_info)

        # Sort each group by frequency descending
        for priority in grouped:
            grouped[priority].sort(key=lambda x: x.frequency, reverse=True)

        return grouped

    def _classify_evidence(
        self, frequency: int
    ) -> Literal["high", "medium", "low", "weak"]:
        """Classify evidence quality based on frequency."""
        if frequency >= 10:
            return "high"
        elif frequency >= 5:
            return "medium"
        elif frequency >= 3:
            return "low"
        else:
            return "weak"

    def _get_affected_names(self, all_names: list[str], token: str) -> list[str]:
        """
        Get names that contain the token in any segment position.

        Uses pattern matching to find token occurrences in raw name strings.
        Checks for token in various grammar patterns:
        - Component prefix: {token}_component_of_*
        - Position: *_at_{token}
        - Process: *_due_to_{token}
        - Object/Geometry: *_of_{token}
        - Geometry prefix: {token}_averaged_*, {token}_volume_*, {token}_area_*
        - Subject/other: token appears as complete word segment
        """
        affected = []
        escaped_token = re.escape(token)

        # Pattern matching on raw strings
        for name in all_names:
            # Check component pattern
            if re.match(rf"^{escaped_token}_component_of_", name):
                affected.append(name)
                continue

            # Check position pattern
            if re.search(rf"_at_{escaped_token}(?:_|$)", name):
                affected.append(name)
                continue

            # Check process pattern
            if re.search(rf"_due_to_{escaped_token}(?:_|$)", name):
                affected.append(name)
                continue

            # Check object/geometry pattern
            if re.search(rf"_of_{escaped_token}(?:_|$)", name):
                affected.append(name)
                continue

            # Check geometry prefix pattern (flux_surface_averaged_*, etc.)
            if re.match(
                rf"^{escaped_token}_(averaged|area|volume|label|coordinate)", name
            ):
                affected.append(name)
                continue

            # Check if token appears as complete word segment (subject, geometric_base, etc.)
            # Must be surrounded by underscores or at boundaries
            pattern = rf"(^|_){escaped_token}(_|$)"
            if re.search(pattern, name):
                affected.append(name)
                continue

        return affected
