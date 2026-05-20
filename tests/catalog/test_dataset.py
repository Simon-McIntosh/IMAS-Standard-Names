"""Tests for the SPA dataset builder (``imas_standard_names.catalog.dataset``).

These tests exercise the conversion from the published per-domain YAML
catalog into the SPA's flat-JSON shape (``CATALOG_VERSION`` +
``CATEGORIES`` + ``GRAMMAR_VOCAB`` + ``NAMES``). Most assertions run
against the real ISNC catalog when it is available; tests that depend
on the live catalog auto-skip when the fixture path is missing so CI
without the ISNC checkout still passes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from imas_standard_names.catalog import build_site_dataset, write_site_dataset
from imas_standard_names.catalog.dataset import (
    _arguments_parent,
    _derive_grammar_facets,
    _extract_sign,
    _humanise_domain,
    _local_ir_peel,
    _normalise_see_also,
    _normalise_sources,
    _normalise_status,
    _parent_token,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ISNC_CATALOG_DIR = Path.home() / "Code/imas-standard-names-catalog/standard_names"


@pytest.fixture
def isnc_catalog_dir() -> Path:
    """Path to the real ISNC catalog. Skips when the checkout is missing."""
    if not ISNC_CATALOG_DIR.exists():
        pytest.skip(f"ISNC catalog checkout not found at {ISNC_CATALOG_DIR}")
    return ISNC_CATALOG_DIR


@pytest.fixture
def isnc_dataset(isnc_catalog_dir: Path) -> dict:
    """Built dataset from the real ISNC catalog (one parse pass for all tests).

    All statuses are now emitted unconditionally, so this fixture no
    longer needs a flag — it uses the plain default.
    """
    return build_site_dataset(isnc_catalog_dir)


@pytest.fixture
def isnc_manifest(isnc_catalog_dir: Path) -> dict:
    """Parsed ``catalog.yml`` manifest from the real ISNC checkout."""
    manifest_path = isnc_catalog_dir.parent / "catalog.yml"
    if not manifest_path.exists():
        pytest.skip("catalog.yml missing alongside catalog directory")
    return yaml.safe_load(manifest_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Pure-helper tests (no catalog dependency)
# ---------------------------------------------------------------------------


class TestHumaniseDomain:
    """``_humanise_domain`` matches the SPA prototype's compact labels."""

    def test_simple_two_word_slug(self) -> None:
        assert _humanise_domain("auxiliary_heating") == "Auxiliary Heating"

    def test_single_word_slug(self) -> None:
        assert _humanise_domain("equilibrium") == "Equilibrium"

    def test_measurement_abbreviated(self) -> None:
        assert (
            _humanise_domain("particle_measurement_diagnostics")
            == "Particle Meas. Diagnostics"
        )

    def test_electromagnetic_abbreviated(self) -> None:
        assert (
            _humanise_domain("electromagnetic_wave_diagnostics")
            == "EM Wave Diagnostics"
        )

    def test_empty_returns_empty(self) -> None:
        assert _humanise_domain("") == ""


class TestExtractSign:
    """``_extract_sign`` separates the ``Sign convention:`` paragraph."""

    def test_extracts_trailing_paragraph(self) -> None:
        doc = (
            "Body of documentation explaining the quantity.\n\n"
            "Sign convention: Positive when the field points outward."
        )
        long, sign = _extract_sign(doc)
        assert long == "Body of documentation explaining the quantity."
        assert sign == "Positive when the field points outward."

    def test_returns_none_when_absent(self) -> None:
        long, sign = _extract_sign("Plain documentation only.")
        assert long == "Plain documentation only."
        assert sign is None

    def test_empty_returns_empty(self) -> None:
        long, sign = _extract_sign("")
        assert long == ""
        assert sign is None


class TestNormaliseSeeAlso:
    """``_normalise_see_also`` strips the ``name:`` prefix."""

    def test_strips_name_prefix(self) -> None:
        assert _normalise_see_also(["name:foo", "name:bar_baz"]) == ["foo", "bar_baz"]

    def test_drops_external_urls(self) -> None:
        assert _normalise_see_also(["https://example.org", "name:foo"]) == ["foo"]

    def test_handles_none(self) -> None:
        assert _normalise_see_also(None) == []


class TestNormaliseSources:
    """``_normalise_sources`` reduces to ``{path, status}`` records."""

    def test_extracts_dd_path_and_status(self) -> None:
        sources = [
            {
                "id": "dd:equilibrium/time_slice/ip",
                "dd_path": "equilibrium/time_slice/ip",
                "status": "composed",
            }
        ]
        assert _normalise_sources(sources) == [
            {"path": "equilibrium/time_slice/ip", "status": "composed"}
        ]

    def test_falls_back_to_id_minus_prefix(self) -> None:
        sources = [{"id": "dd:foo/bar", "status": "attached"}]
        assert _normalise_sources(sources) == [
            {"path": "foo/bar", "status": "attached"}
        ]

    def test_handles_none(self) -> None:
        assert _normalise_sources(None) == []


class TestGrammarFacets:
    """``_derive_grammar_facets`` extracts the IR signals the emitter needs."""

    def test_locus_detected(self) -> None:
        facets = _derive_grammar_facets("safety_factor_at_magnetic_axis")
        assert facets.has_locus is True
        assert facets.locus_token == "magnetic_axis"

    def test_projection_detected(self) -> None:
        facets = _derive_grammar_facets("poloidal_magnetic_field")
        assert facets.has_projection is True
        assert facets.axis == "poloidal"

    def test_pure_base_has_no_facets(self) -> None:
        facets = _derive_grammar_facets("safety_factor")
        assert facets.has_projection is False
        assert facets.has_locus is False
        assert facets.base_token == "safety_factor"


# ---------------------------------------------------------------------------
# Real-catalog tests — auto-skip when ISNC checkout is missing
# ---------------------------------------------------------------------------


class TestDatasetShape:
    """Top-level dataset keys and counts derive from the actual YAML files.

    The CATALOG_VERSION label and category counts use ``len(names)`` —
    the actual number of records emitted — rather than the manifest's
    ``published_count``. (Manifest counts can lag if the codex export
    filter excluded entries after the manifest was written, and we
    want the SPA to show the truth.)
    """

    def test_loads_isnc_catalog(self, isnc_dataset: dict) -> None:
        assert "NAMES" in isnc_dataset
        assert "CATEGORIES" in isnc_dataset
        assert "GRAMMAR_VOCAB" in isnc_dataset
        assert "CATALOG_VERSION" in isnc_dataset

        names = isnc_dataset["NAMES"]
        assert len(names) > 0, "real ISNC catalog must yield at least one record"

    def test_catalog_version_includes_grammar_and_count(
        self, isnc_dataset: dict, isnc_manifest: dict
    ) -> None:
        version = isnc_dataset["CATALOG_VERSION"]
        names = isnc_dataset["NAMES"]
        # Manifest's grammar_version always appears verbatim.
        assert isnc_manifest["grammar_version"] in version
        # The displayed count is the actual emitted count, not the
        # manifest's possibly-stale ``published_count`` claim.
        assert str(len(names)) in version

    def test_categories_derived(self, isnc_dataset: dict, isnc_manifest: dict) -> None:
        cats = isnc_dataset["CATEGORIES"]
        # Every domain in the manifest should appear in CATEGORIES.
        category_ids = {c["id"] for c in cats}
        for domain in isnc_manifest["domains_included"]:
            assert domain in category_ids, f"domain {domain} missing from CATEGORIES"

        # Counts sum to total NAMES length.
        total = sum(c["count"] for c in cats)
        assert total == len(isnc_dataset["NAMES"])

        # Counts decrease (descending).
        counts = [c["count"] for c in cats]
        assert counts == sorted(counts, reverse=True)


def _find_record(dataset: dict, name: str) -> dict:
    """Helper — fetch a NAMES record by name, asserting it exists."""
    for record in dataset["NAMES"]:
        if record["name"] == name:
            return record
    pytest.fail(f"record {name!r} not found in dataset")


class TestRecordShape:
    """A representative NAMES record carries all SPA-expected fields."""

    def test_plasma_inductance_full_shape(self, isnc_dataset: dict) -> None:
        record = _find_record(isnc_dataset, "plasma_inductance")

        # Identity
        assert record["name"] == "plasma_inductance"
        assert record["category"] == "equilibrium"

        # Required keys all present. ``display_kind`` / ``kind`` have
        # been retired; ``algebra`` (scalar/vector/tensor/complex/metadata)
        # is the canonical kind axis.
        required = {
            "name",
            "category",
            "group",
            "parent",
            "algebra",
            "status",
            "unit",
            "tags",
            "short",
            "long",
            "sign",
            "seeAlso",
            "arguments",
            "sources",
            "parse",
            "components",
            "magnitude",
            "children",
        }
        assert required.issubset(record.keys()), (
            f"missing keys: {required - set(record.keys())}"
        )
        # The retired synthetic kind axes must NOT be present.
        assert "display_kind" not in record
        assert "kind" not in record

        # Type checks.
        assert isinstance(record["tags"], list)
        assert isinstance(record["seeAlso"], list)
        assert isinstance(record["arguments"], list)
        assert isinstance(record["sources"], list)
        assert isinstance(record["parse"], list)
        assert isinstance(record["components"], list)
        assert isinstance(record["children"], list)
        assert all(
            isinstance(seg, dict) and {"role", "text"}.issubset(seg.keys())
            for seg in record["parse"]
        )

    def test_unit_present_for_physical_quantity(self, isnc_dataset: dict) -> None:
        record = _find_record(isnc_dataset, "plasma_inductance")
        assert record["unit"] == "H"


class TestGrammarMetadata:
    """Structural cues (axis, locus) still surface on the record even
    though ``display_kind`` no longer does."""

    def test_poloidal_magnetic_field_keeps_axis(self, isnc_dataset: dict) -> None:
        record = _find_record(isnc_dataset, "poloidal_magnetic_field")
        assert record["axis"] == "poloidal"
        # Vector components inherit vector algebra from their projection.
        assert record["algebra"] == "vector"

    def test_safety_factor_at_magnetic_axis_keeps_locus(
        self, isnc_dataset: dict
    ) -> None:
        record = _find_record(isnc_dataset, "safety_factor_at_magnetic_axis")
        assert record["locus"] == "magnetic_axis"


class TestAlgebraAxis:
    """Algebraic kind (scalar/vector/tensor/complex/metadata) is the sole
    kind axis on each record. The retired synthetic ``display_kind`` is
    gone from the JSON output."""

    def test_magnetic_field_is_vector(self, isnc_dataset: dict) -> None:
        record = _find_record(isnc_dataset, "magnetic_field")
        assert record["algebra"] == "vector"

    def test_scalar_default(self, isnc_dataset: dict) -> None:
        record = _find_record(isnc_dataset, "electron_temperature")
        assert record["algebra"] == "scalar"

    def test_every_record_has_algebra(self, isnc_dataset: dict) -> None:
        valid = {"scalar", "vector", "tensor", "complex", "metadata"}
        for record in isnc_dataset["NAMES"]:
            assert record["algebra"] in valid, (
                f"{record['name']}: bad algebra {record['algebra']!r}"
            )

    def test_magnitude_is_scalar(self, isnc_dataset: dict) -> None:
        # magnitude_of_<vector> is a true scalar (rotation-invariant norm).
        import pytest

        rec = next(
            (
                r
                for r in isnc_dataset["NAMES"]
                if r["name"] == "magnetic_field_magnitude"
            ),
            None,
        )
        if rec is None:
            pytest.skip("magnetic_field_magnitude not in catalog")
        assert rec["algebra"] == "scalar"


class TestVectorReverseLinks:
    """Vectors carry ``components`` and (when present) ``magnitude``."""

    def test_magnetic_field_components(self, isnc_dataset: dict) -> None:
        record = _find_record(isnc_dataset, "magnetic_field")
        components = record["components"]
        assert len(components) >= 2, (
            f"magnetic_field should have ≥2 components, got {components}"
        )
        # Each component carries name + axis; axes are unique.
        axes = {c["axis"] for c in components}
        assert len(axes) == len(components)
        for c in components:
            assert isinstance(c["name"], str) and c["name"]
            assert isinstance(c["axis"], str) and c["axis"]

    def test_scalar_has_empty_components(self, isnc_dataset: dict) -> None:
        record = _find_record(isnc_dataset, "electron_temperature")
        assert record["components"] == []
        assert record["magnitude"] is None

    def test_magnitude_only_when_catalog_has_it(self, isnc_dataset: dict) -> None:
        """``magnitude`` is set only when ``magnitude_of_<name>`` exists.

        Source-driven invariant: no speculative magnitude creation.
        Current catalog has no magnitudes of vectors, so all vectors'
        ``magnitude`` should be None.
        """
        record = _find_record(isnc_dataset, "magnetic_field")
        # Either it exists in the catalog (string), or None — never auto-faked.
        magnitude = record["magnitude"]
        assert magnitude is None or isinstance(magnitude, str)
        if isinstance(magnitude, str):
            # If set, the referenced name must exist in the dataset.
            assert any(n["name"] == magnitude for n in isnc_dataset["NAMES"])

    def test_children_index(self, isnc_dataset: dict) -> None:
        record = _find_record(isnc_dataset, "magnetic_field")
        children = record["children"]
        # magnetic_field has projection + qualifier children.
        assert any(c["operator_kind"] == "projection" for c in children), (
            f"expected projection children, got {children}"
        )


class TestSubject:
    """``subject`` is the first qualifier matching the closed Subject enum."""

    def test_electron_subject(self, isnc_dataset: dict) -> None:
        assert (
            _find_record(isnc_dataset, "electron_temperature")["subject"] == "electron"
        )

    def test_ion_subject(self, isnc_dataset: dict) -> None:
        assert _find_record(isnc_dataset, "ion_temperature")["subject"] == "ion"

    def test_unqualified_has_no_subject(self, isnc_dataset: dict) -> None:
        # ``magnetic_field`` is a bare base — no subject qualifier.
        assert _find_record(isnc_dataset, "magnetic_field")["subject"] is None


class TestParseSegments:
    """Parse segments concatenate back to the input name (modulo separators)."""

    @pytest.mark.parametrize(
        "name",
        [
            "total_plasma_current",
            "poloidal_magnetic_field",
            "safety_factor_at_magnetic_axis",
            "magnetic_field_magnitude",
            "flux_surface_averaged_magnetic_field",
            "minimum_safety_factor",
        ],
    )
    def test_parse_segments_cover_name_tokens(
        self, isnc_dataset: dict, name: str
    ) -> None:
        records = [r for r in isnc_dataset["NAMES"] if r["name"] == name]
        if not records:
            pytest.skip(f"{name} not present in current catalog")
        segments = records[0]["parse"]
        # Every token segment carries a non-empty text. Joining with
        # underscores (after stripping any leading `_` artefacts) should
        # cover all underscore-separated tokens in the original name.
        original_tokens = set(name.split("_"))
        emitted_tokens: set[str] = set()
        for seg in segments:
            text = seg["text"]
            assert text, f"empty text segment in parse: {seg!r}"
            for piece in text.split("_"):
                if piece:
                    emitted_tokens.add(piece)
        # Tokens emitted should at minimum include all original tokens.
        missing = original_tokens - emitted_tokens
        assert not missing, f"parse missing tokens {missing} for {name}"

    def test_parse_failure_is_graceful(self) -> None:
        # A deliberately invalid base token (looks like a name but won't
        # resolve in the closed vocabulary) must round-trip to a single
        # ``unparseable`` segment instead of crashing the build.
        from imas_standard_names.catalog.dataset import _derive_grammar_facets

        facets = _derive_grammar_facets("definitely_not_a_known_thing_xyz")
        assert facets.parsed is False
        assert len(facets.parse_segments) == 1
        assert facets.parse_segments[0]["role"] == "unparseable"

    def test_unparseable_does_not_crash_dataset(
        self, tmp_path: Path, isnc_dataset: dict
    ) -> None:
        # Construct a tiny standalone YAML with an unparseable name and
        # run the builder on it — the result should still produce a
        # record with an ``unparseable`` parse segment.
        domain_yaml = tmp_path / "test_domain.yml"
        domain_yaml.write_text(
            yaml.safe_dump(
                [
                    {
                        "name": "definitely_not_a_known_thing_xyz",
                        "kind": "scalar",
                        "status": "active",
                        "description": "Test entry that the parser cannot decompose.",
                        "documentation": "This entry exists only to exercise the unparseable fallback.",
                        "unit": "1",
                        "physics_domain": "test_domain",
                    }
                ]
            ),
            encoding="utf-8",
        )

        dataset = build_site_dataset(tmp_path)
        assert len(dataset["NAMES"]) == 1
        record = dataset["NAMES"][0]
        assert record["parse"][0]["role"] == "unparseable"


class TestSeeAlsoNormalisation:
    """``links: [name:foo]`` flattens to ``seeAlso: ['foo']``."""

    def test_name_prefix_stripped(self, isnc_dataset: dict) -> None:
        # Find a record with at least one internal link.
        for record in isnc_dataset["NAMES"]:
            if record["seeAlso"]:
                for ref in record["seeAlso"]:
                    assert not ref.startswith("name:"), (
                        f"seeAlso entry {ref!r} should not retain 'name:' prefix"
                    )
                return
        pytest.skip("no records with seeAlso links in current catalog")


class TestSourcesNormalisation:
    """Sources become ``[{path, status}]`` records."""

    def test_sources_have_path_and_status(self, isnc_dataset: dict) -> None:
        for record in isnc_dataset["NAMES"]:
            if record["sources"]:
                for src in record["sources"]:
                    assert "path" in src
                    assert "status" in src
                    assert src["path"]  # non-empty
                return
        pytest.skip("no records with sources in current catalog")


# ---------------------------------------------------------------------------
# Roundtrip — write + load
# ---------------------------------------------------------------------------


class TestWriteSiteDataset:
    """``write_site_dataset`` produces valid JSON on disk."""

    def test_writes_to_disk(self, isnc_catalog_dir: Path, tmp_path: Path) -> None:
        out = tmp_path / "dataset.json"
        count = write_site_dataset(isnc_catalog_dir, out)

        assert out.exists()
        assert count > 0
        # Round-trip the JSON.
        data = json.loads(out.read_text(encoding="utf-8"))
        assert len(data["NAMES"]) == count


# ---------------------------------------------------------------------------
# Parent resolution — peel one layer (operator | projection | qualifier | locus)
# ---------------------------------------------------------------------------


class TestLocalIrPeel:
    """Standalone IR peel: one layer at a time, recursion is implicit.

    The rc8 SPA shortcut to ``ir.base.token`` collapsed every layer
    in one go — these tests pin the corrected per-layer behaviour
    so future refactors cannot regress.
    """

    def test_leaf_returns_none(self):
        assert _local_ir_peel("temperature") is None
        assert _local_ir_peel("elongation") is None

    def test_qualifier_with_locus_peels_qualifier(self):
        # The headline regression — `upper_elongation_of_plasma_boundary`
        # used to report parent=`elongation` (skipping the boundary
        # locus); should now stay on the boundary side of the family.
        assert (
            _local_ir_peel("upper_elongation_of_plasma_boundary")
            == "elongation_of_plasma_boundary"
        )
        assert (
            _local_ir_peel("lower_elongation_of_plasma_boundary")
            == "elongation_of_plasma_boundary"
        )

    def test_locus_only_peels_locus(self):
        assert _local_ir_peel("elongation_of_plasma_boundary") == "elongation"
        assert _local_ir_peel("area_of_plasma_boundary") == "area"
        assert _local_ir_peel("safety_factor_at_magnetic_axis") == "safety_factor"

    def test_qualifier_only_peels_qualifier(self):
        assert _local_ir_peel("electron_temperature") == "temperature"
        assert _local_ir_peel("ion_pressure") == "pressure"

    def test_two_qualifiers_peels_outermost_only(self):
        # `volume_averaged_ion_temperature` — two qualifiers, peel one
        # at a time. The inner SN runs its own derivation on the next
        # hop.
        assert _local_ir_peel("volume_averaged_ion_temperature") == "ion_temperature"

    def test_unparseable_returns_none(self):
        assert _local_ir_peel("garbage_name_!@#") is None


class TestArgumentsParent:
    """When the YAML carries an ``arguments`` block (canonical, graph-
    derived), prefer it over local heuristics."""

    def test_first_argument_wins(self):
        entry = {"arguments": [{"name": "elongation_of_plasma_boundary"}]}
        assert (
            _arguments_parent("upper_elongation_of_plasma_boundary", entry)
            == "elongation_of_plasma_boundary"
        )

    def test_self_loop_skipped(self):
        entry = {"arguments": [{"name": "upper_elongation_of_plasma_boundary"}]}
        assert _arguments_parent("upper_elongation_of_plasma_boundary", entry) is None

    def test_missing_arguments_returns_none(self):
        assert _arguments_parent("x", {}) is None
        assert _arguments_parent("x", {"arguments": None}) is None
        assert _arguments_parent("x", {"arguments": []}) is None

    def test_falls_through_to_second_arg_when_first_is_self(self):
        entry = {
            "arguments": [
                {"name": "upper_elongation_of_plasma_boundary"},
                {"name": "elongation_of_plasma_boundary"},
            ]
        }
        assert (
            _arguments_parent("upper_elongation_of_plasma_boundary", entry)
            == "elongation_of_plasma_boundary"
        )


class TestParentToken:
    """End-to-end ``_parent_token`` resolution: arguments > local peel > facets."""

    def test_arguments_preferred_over_local_peel(self):
        # If the YAML carries arguments, use them even when local peel
        # would say something different.
        entry = {"arguments": [{"name": "some_specific_parent"}]}
        facets = _derive_grammar_facets("upper_elongation_of_plasma_boundary")
        assert (
            _parent_token("upper_elongation_of_plasma_boundary", facets, entry)
            == "some_specific_parent"
        )

    def test_local_peel_used_when_arguments_missing(self):
        facets = _derive_grammar_facets("upper_elongation_of_plasma_boundary")
        assert (
            _parent_token("upper_elongation_of_plasma_boundary", facets, {})
            == "elongation_of_plasma_boundary"
        )

    def test_leaf_returns_none(self):
        facets = _derive_grammar_facets("elongation")
        assert _parent_token("elongation", facets, {}) is None

    def test_legacy_callsite_without_entry(self):
        # Backwards-compat: callers that don't pass `entry` still get
        # the corrected one-layer peel.
        facets = _derive_grammar_facets("electron_temperature")
        assert _parent_token("electron_temperature", facets) == "temperature"


# ---------------------------------------------------------------------------
# Status normalisation + include-draft filtering
# ---------------------------------------------------------------------------


class TestNormaliseStatus:
    """Legacy status values map to the canonical set; unknowns drop."""

    def test_canonical_values_pass_through(self) -> None:
        for value in ("draft", "active", "deprecated", "superseded"):
            assert _normalise_status(value) == value

    def test_legacy_drafted_maps_to_draft(self) -> None:
        assert _normalise_status("drafted") == "draft"

    def test_legacy_accepted_maps_to_active(self) -> None:
        assert _normalise_status("accepted") == "active"

    def test_legacy_published_maps_to_active(self) -> None:
        assert _normalise_status("published") == "active"

    def test_unknown_value_returns_none(self) -> None:
        assert _normalise_status("not_a_real_status") is None
        assert _normalise_status("nonsense") is None

    def test_missing_value_defaults_to_draft(self) -> None:
        # Catalog entries written before status was required should fall
        # to "draft" rather than be silently dropped.
        assert _normalise_status(None) == "draft"
        assert _normalise_status("") == "draft"


class TestCanonicalKinds:
    """Output JSON exposes only the five schema kinds — no display_kind."""

    def test_no_display_kind_in_records(self, isnc_dataset: dict) -> None:
        for record in isnc_dataset["NAMES"]:
            assert "display_kind" not in record
            assert "kind" not in record  # alias also dropped

    def test_algebra_is_one_of_five_canonical(self, isnc_dataset: dict) -> None:
        valid = {"scalar", "vector", "tensor", "complex", "metadata"}
        for record in isnc_dataset["NAMES"]:
            assert record["algebra"] in valid


class TestStatusFiltering:
    """All canonical statuses are always emitted; unknown statuses are dropped."""

    def _write_yaml(self, path: Path, entries: list[dict]) -> None:
        path.write_text(yaml.safe_dump(entries), encoding="utf-8")

    def test_default_emit_includes_all_known_statuses(self, tmp_path: Path) -> None:
        """build_site_dataset emits draft, deprecated, superseded, and active."""
        self._write_yaml(
            tmp_path / "test_domain.yml",
            [
                {
                    "name": "alpha",
                    "physics_domain": "x",
                    "kind": "scalar",
                    "unit": "1",
                    "status": "active",
                    "description": "A",
                    "documentation": "doc",
                },
                {
                    "name": "beta",
                    "physics_domain": "x",
                    "kind": "scalar",
                    "unit": "1",
                    "status": "draft",
                    "description": "B",
                    "documentation": "doc",
                },
                {
                    "name": "gamma",
                    "physics_domain": "x",
                    "kind": "scalar",
                    "unit": "1",
                    "status": "deprecated",
                    "description": "C",
                    "documentation": "doc",
                },
                {
                    "name": "delta",
                    "physics_domain": "x",
                    "kind": "scalar",
                    "unit": "1",
                    "status": "superseded",
                    "description": "D",
                    "documentation": "doc",
                },
            ],
        )
        ds = build_site_dataset(tmp_path)
        names = {r["name"] for r in ds["NAMES"]}
        assert names == {"alpha", "beta", "gamma", "delta"}

    def test_no_include_draft_parameter(self) -> None:
        """build_site_dataset signature must not contain include_draft."""
        import inspect

        sig = inspect.signature(build_site_dataset)
        assert "include_draft" not in sig.parameters, (
            "include_draft has been removed — the function always emits all statuses"
        )

    def test_superseded_by_round_trips(self, tmp_path: Path) -> None:
        """superseded_by from YAML is present on the emitted record."""
        self._write_yaml(
            tmp_path / "test_domain.yml",
            [
                {
                    "name": "old_name",
                    "physics_domain": "x",
                    "kind": "scalar",
                    "unit": "1",
                    "status": "superseded",
                    "superseded_by": "new_name",
                    "description": "Old",
                    "documentation": "doc",
                },
                {
                    "name": "new_name",
                    "physics_domain": "x",
                    "kind": "scalar",
                    "unit": "1",
                    "status": "active",
                    "description": "New",
                    "documentation": "doc",
                },
            ],
        )
        ds = build_site_dataset(tmp_path)
        records = {r["name"]: r for r in ds["NAMES"]}
        assert records["old_name"]["superseded_by"] == "new_name"
        assert records["new_name"]["superseded_by"] is None

    def test_legacy_status_values_mapped(self, tmp_path: Path) -> None:
        self._write_yaml(
            tmp_path / "test_domain.yml",
            [
                {
                    "name": "old_drafted",
                    "physics_domain": "x",
                    "kind": "scalar",
                    "unit": "1",
                    "status": "drafted",
                    "description": "D",
                    "documentation": "doc",
                },
                {
                    "name": "old_accepted",
                    "physics_domain": "x",
                    "kind": "scalar",
                    "unit": "1",
                    "status": "accepted",
                    "description": "E",
                    "documentation": "doc",
                },
                {
                    "name": "old_published",
                    "physics_domain": "x",
                    "kind": "scalar",
                    "unit": "1",
                    "status": "published",
                    "description": "F",
                    "documentation": "doc",
                },
            ],
        )
        # All three legacy values normalise and are emitted.
        ds = build_site_dataset(tmp_path)
        names = {r["name"]: r["status"] for r in ds["NAMES"]}
        assert names == {
            "old_drafted": "draft",
            "old_accepted": "active",
            "old_published": "active",
        }

    def test_unknown_status_dropped(self, tmp_path: Path) -> None:
        self._write_yaml(
            tmp_path / "test_domain.yml",
            [
                {
                    "name": "weird",
                    "physics_domain": "x",
                    "kind": "scalar",
                    "unit": "1",
                    "status": "not_a_real_status",
                    "description": "W",
                    "documentation": "doc",
                },
                {
                    "name": "ok",
                    "physics_domain": "x",
                    "kind": "scalar",
                    "unit": "1",
                    "status": "active",
                    "description": "O",
                    "documentation": "doc",
                },
            ],
        )
        ds = build_site_dataset(tmp_path)
        names = {r["name"] for r in ds["NAMES"]}
        assert names == {"ok"}, "unknown status must be silently dropped"


class TestSortKeys:
    """``sort_tier`` and ``sort_axis_index`` drive canonical grouping order."""

    def test_every_record_has_sort_keys(self, isnc_dataset: dict) -> None:
        for record in isnc_dataset["NAMES"]:
            assert isinstance(record.get("sort_tier"), int)
            assert isinstance(record.get("sort_axis_index"), int)
            assert 0 <= record["sort_tier"] <= 7
            assert (
                0 <= record["sort_axis_index"] <= 5 or record["sort_axis_index"] == 99
            )

    def test_magnetic_field_family_order(self, isnc_dataset: dict) -> None:
        """Snapshot the magnetic_field family ordering.

        Expected order per Design Review §8:
            magnetic_field           (tier 0, vector base)
            radial_magnetic_field    (tier 1, axis index 0)
            toroidal_magnetic_field  (tier 1, axis index 1)
            vertical_magnetic_field  (tier 1, axis index 2)
            poloidal_magnetic_field  (tier 1, axis index 3)
            magnetic_field_magnitude (tier 2)
            flux_surface_averaged_magnetic_field (tier 3)

        Names not present in the catalog snapshot are skipped — the
        relative order of those that ARE present must match the above.
        """
        expected = [
            "magnetic_field",
            "radial_magnetic_field",
            "toroidal_magnetic_field",
            "vertical_magnetic_field",
            "poloidal_magnetic_field",
            "magnetic_field_magnitude",
            "flux_surface_averaged_magnetic_field",
        ]
        # Build a map name -> (tier, axis_idx) for fast assertion.
        records = {r["name"]: r for r in isnc_dataset["NAMES"] if r["name"] in expected}
        if len(records) < 2:
            pytest.skip(
                f"need at least 2 magnetic_field family entries in catalog, "
                f"got {len(records)}"
            )

        # Sort the expected names that DO exist by (tier, axis_idx, length, name)
        # and confirm the order matches the expected list (filtered to
        # only-present names).
        present_expected = [n for n in expected if n in records]

        def sort_key(name: str):
            r = records[name]
            return (r["sort_tier"], r["sort_axis_index"], len(name), name)

        sorted_present = sorted(present_expected, key=sort_key)
        assert sorted_present == present_expected, (
            f"family ordering wrong:\n"
            f"  expected (present subset): {present_expected}\n"
            f"  got after sort:            {sorted_present}"
        )

    def test_vector_base_is_tier_zero(self, isnc_dataset: dict) -> None:
        record = _find_record(isnc_dataset, "magnetic_field")
        assert record["sort_tier"] == 0
        assert record["sort_axis_index"] == 99  # no axis projection

    def test_component_carries_axis_index(self, isnc_dataset: dict) -> None:
        record = _find_record(isnc_dataset, "poloidal_magnetic_field")
        assert record["sort_tier"] == 1
        assert record["sort_axis_index"] == 3  # poloidal

    def test_magnitude_is_tier_two(self, isnc_dataset: dict) -> None:
        records = [
            r for r in isnc_dataset["NAMES"] if r["name"] == "magnetic_field_magnitude"
        ]
        if not records:
            pytest.skip("magnetic_field_magnitude not present in current catalog")
        assert records[0]["sort_tier"] == 2
