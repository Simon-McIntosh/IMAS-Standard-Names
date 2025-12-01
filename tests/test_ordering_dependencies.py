import pytest

from imas_standard_names.ordering import ordered_model_names
from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.yaml_store import YamlStore


@pytest.fixture
def catalog_with_vectors(tmp_path, copy_examples):
    """Create a catalog with vector examples for testing ordering."""
    catalog_dir = tmp_path / "ordering_catalog"
    catalog_dir.mkdir()
    copy_examples(catalog_dir, count=20, kind=None)
    return catalog_dir


def test_vector_components_before_vectors(catalog_with_vectors):
    root = catalog_with_vectors
    store = YamlStore(root)
    models = store.load()
    order = list(ordered_model_names(models))
    index = {name: i for i, name in enumerate(order)}

    # For each vector ensure all its component names appear earlier.
    for m in models:
        if getattr(m, "kind", "").endswith("vector"):
            for comp in (getattr(m, "components", {}) or {}).values():
                assert index[comp] < index[m.name], (
                    f"Component {comp} not before vector {m.name}"
                )


def test_provenance_base_before_derived(catalog_with_vectors):
    root = catalog_with_vectors
    store = YamlStore(root)
    models = store.load()
    order = list(ordered_model_names(models))
    index = {name: i for i, name in enumerate(order)}

    for m in models:
        prov = getattr(m, "provenance", None)
        if prov:
            base = getattr(prov, "base", None)
            if base and base in index:
                assert index[base] < index[m.name], (
                    f"Base {base} not before derived {m.name}"
                )


def test_repository_initializes_without_fk_errors(sample_catalog):
    # Use sample catalog with known entries
    repo = sample_catalog
    # Simple sanity: catalog should have entries
    entries = list(repo.list())
    assert len(entries) > 0, "Catalog should have at least one entry"
