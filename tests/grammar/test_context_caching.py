"""get_grammar_context memoises its expensive aggregate in process and on disk.

The payload includes a full catalog scan (usage statistics); external pipelines
construct grammar-validated models in tight loops, so a rebuild per call is
prohibitive, and they invoke a fresh process per operation, so an in-process memo
alone buys nothing. The aggregate is therefore also persisted to a per-user cache
directory under a fingerprint of every input, and calls receive deep copies,
keeping caller-side mutation away from the shared cache.
"""

import json
import time

import pytest

from imas_standard_names.grammar import context
from imas_standard_names.grammar.context import get_grammar_context


def test_second_call_is_cheap():
    get_grammar_context()  # warm (may pay the catalog scan)
    start = time.perf_counter()
    get_grammar_context()
    assert time.perf_counter() - start < 1.0


def test_calls_return_equal_but_independent_payloads():
    first = get_grammar_context()
    second = get_grammar_context()
    assert first == second
    assert first is not second

    first["naming_guidance"] = "mutated"
    first["applicability"]["include"].append("mutated")
    fresh = get_grammar_context()
    assert fresh["naming_guidance"] != "mutated"
    assert "mutated" not in fresh["applicability"]["include"]


# ---------------------------------------------------------------------------
# Cross-process cache
# ---------------------------------------------------------------------------


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    """Route the disk cache into a temporary directory, empty per test."""
    monkeypatch.delenv(context.CACHE_ENABLE_ENV, raising=False)
    monkeypatch.setenv(context.CACHE_DIR_ENV, str(tmp_path))
    context._load_or_build_context.cache_clear()
    yield tmp_path / "grammar-context"
    context._load_or_build_context.cache_clear()


def _entries(cache_dir):
    return sorted(cache_dir.glob("*.json")) if cache_dir.exists() else []


def test_payload_survives_a_json_round_trip():
    """Serialisation must be lossless: the cache stores JSON.

    A tuple or enum reaching the payload would come back as something else and
    a cache hit would then disagree with a rebuild.
    """
    built = context._build_full_context()
    assert json.loads(json.dumps(built)) == built


def test_stored_entry_equals_the_freshly_built_payload(cache_dir):
    payload = get_grammar_context()
    entries = _entries(cache_dir)
    assert len(entries) == 1
    assert json.loads(entries[0].read_text(encoding="utf-8")) == payload
    assert payload == context._build_full_context()


def test_later_process_loads_the_entry_instead_of_rebuilding(cache_dir, monkeypatch):
    first = get_grammar_context()
    assert len(_entries(cache_dir)) == 1

    # A fresh process starts with an empty memo; make any rebuild attempt fail
    # so only a successful disk load can satisfy the call.
    context._load_or_build_context.cache_clear()
    monkeypatch.setattr(
        context,
        "_build_full_context",
        lambda: pytest.fail("rebuilt instead of loading the cached payload"),
    )
    assert get_grammar_context() == first


def test_unreadable_entry_degrades_to_a_rebuild(cache_dir):
    get_grammar_context()
    entry = _entries(cache_dir)[0]
    entry.write_text("{ this is not json", encoding="utf-8")

    context._load_or_build_context.cache_clear()
    payload = get_grammar_context()
    assert payload["canonical_pattern"]
    assert json.loads(entry.read_text(encoding="utf-8")) == payload


def test_truncated_entry_degrades_to_a_rebuild(cache_dir):
    """A half-written file (a reader racing a writer) must not be trusted."""
    get_grammar_context()
    entry = _entries(cache_dir)[0]
    whole = entry.read_text(encoding="utf-8")
    entry.write_text(whole[: len(whole) // 2], encoding="utf-8")

    context._load_or_build_context.cache_clear()
    assert get_grammar_context()["canonical_pattern"]


def test_unwritable_cache_directory_still_returns_a_payload(tmp_path, monkeypatch):
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("", encoding="utf-8")
    monkeypatch.delenv(context.CACHE_ENABLE_ENV, raising=False)
    monkeypatch.setenv(context.CACHE_DIR_ENV, str(blocker))
    context._load_or_build_context.cache_clear()
    try:
        assert get_grammar_context()["canonical_pattern"]
    finally:
        context._load_or_build_context.cache_clear()


def test_writes_are_atomic_leaving_no_partial_files(cache_dir):
    get_grammar_context()
    assert [path.name for path in cache_dir.iterdir()] == [_entries(cache_dir)[0].name]


def test_disable_flag_bypasses_the_disk_cache(cache_dir, monkeypatch):
    monkeypatch.setenv(context.CACHE_ENABLE_ENV, "0")
    assert not context._cache_enabled()
    assert get_grammar_context()["canonical_pattern"]
    assert _entries(cache_dir) == []


def test_superseded_entries_are_pruned(cache_dir):
    get_grammar_context()
    cache_dir.mkdir(parents=True, exist_ok=True)
    for index in range(context._CACHE_RETAIN + 4):
        (cache_dir / f"{index:032x}.json").write_text("{}", encoding="utf-8")
    context._prune_cache(cache_dir)
    assert len(_entries(cache_dir)) == context._CACHE_RETAIN


# ---------------------------------------------------------------------------
# Key invalidation
# ---------------------------------------------------------------------------


def test_fingerprint_covers_the_specification_and_the_vocabularies():
    paths = set(context._fingerprint_paths())
    grammar = context._GRAMMAR_DIR
    assert grammar / "specification.yml" in paths
    assert grammar / "vocabularies" / "physical_bases.yml" in paths
    assert grammar / "vocabularies" / "locus_registry.yml" in paths
    assert grammar / "context.py" in paths
    assert context._PACKAGE_DIR / "models.py" in paths


@pytest.fixture
def synthetic_sources(tmp_path, monkeypatch):
    """A miniature package tree standing in for the real fingerprint inputs."""
    package = tmp_path / "package"
    grammar = package / "grammar"
    grammar.mkdir(parents=True)
    (package / "builder.py").write_text("token = 'a'\n", encoding="utf-8")
    (grammar / "specification.yml").write_text("segments: []\n", encoding="utf-8")
    monkeypatch.setattr(context, "_PACKAGE_DIR", package)
    monkeypatch.setattr(context, "_GRAMMAR_DIR", grammar)
    return package, grammar


def test_edited_vocabulary_changes_the_key(synthetic_sources):
    _, grammar = synthetic_sources
    before = context._cache_key()
    (grammar / "specification.yml").write_text("segments: [base]\n", encoding="utf-8")
    assert context._cache_key() != before


def test_edited_module_changes_the_key(synthetic_sources):
    package, _ = synthetic_sources
    before = context._cache_key()
    (package / "builder.py").write_text("token = 'b'\n", encoding="utf-8")
    assert context._cache_key() != before


def test_added_vocabulary_file_changes_the_key(synthetic_sources):
    _, grammar = synthetic_sources
    before = context._cache_key()
    (grammar / "extra.yml").write_text("tokens: []\n", encoding="utf-8")
    assert context._cache_key() != before


def test_distribution_version_participates_in_the_key(synthetic_sources, monkeypatch):
    before = context._cache_key()
    monkeypatch.setattr(context, "_distribution_version", lambda: "0.0.0+synthetic")
    assert context._cache_key() != before


@pytest.fixture
def synthetic_catalog(tmp_path, monkeypatch):
    """A miniature catalog directory standing in for the scanned catalog."""
    root = tmp_path / "catalog"
    (root / "equilibrium").mkdir(parents=True)
    entry = root / "equilibrium" / "safety_factor.yml"
    entry.write_text("name: safety_factor\n", encoding="utf-8")
    monkeypatch.setattr(
        "imas_standard_names.paths.get_default_catalog_path", lambda: root
    )
    return root, entry


def test_edited_catalog_entry_changes_the_key(synthetic_catalog):
    _, entry = synthetic_catalog
    before = context._cache_key()
    entry.write_text("name: safety_factor\nunit: '1'\n", encoding="utf-8")
    assert context._cache_key() != before


def test_added_catalog_entry_changes_the_key(synthetic_catalog):
    root, _ = synthetic_catalog
    before = context._cache_key()
    (root / "equilibrium" / "plasma_current.yml").write_text(
        "name: plasma_current\n", encoding="utf-8"
    )
    assert context._cache_key() != before


def test_removed_catalog_entry_changes_the_key(synthetic_catalog):
    _, entry = synthetic_catalog
    before = context._cache_key()
    entry.unlink()
    assert context._cache_key() != before


def test_appearing_catalog_changes_the_key(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "imas_standard_names.paths.get_default_catalog_path", lambda: None
    )
    absent = context._cache_key()
    monkeypatch.setattr(
        "imas_standard_names.paths.get_default_catalog_path", lambda: tmp_path
    )
    assert context._cache_key() != absent


def test_relocated_catalog_changes_the_key(tmp_path, monkeypatch):
    """Two catalogs with identical file listings are still distinct inputs."""
    keys = []
    for name in ("left", "right"):
        root = tmp_path / name
        root.mkdir()
        (root / "entry.yml").write_text("name: x\n", encoding="utf-8")
        monkeypatch.setattr(
            "imas_standard_names.paths.get_default_catalog_path", lambda root=root: root
        )
        keys.append(context._cache_key())
    assert keys[0] != keys[1]


def test_derived_catalog_artifacts_do_not_change_the_key(synthetic_catalog):
    """The generated SQLite catalog is an output, not an input."""
    root, _ = synthetic_catalog
    before = context._cache_key()
    derived = root / ".catalog"
    derived.mkdir()
    (derived / "catalog.db").write_bytes(b"sqlite")
    assert context._cache_key() == before
