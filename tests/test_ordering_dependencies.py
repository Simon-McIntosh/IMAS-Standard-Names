from imas_standard_names.paths import resolve_root
from imas_standard_names.yaml_store import YamlStore
from imas_standard_names.ordering import ordered_model_names
from imas_standard_names.repository import StandardNameRepository


def test_vector_components_before_vectors():
    root = resolve_root(None)
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


def test_provenance_base_before_derived():
    root = resolve_root(None)
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


def test_repository_initializes_without_fk_errors():
    # This will raise if FK ordering still broken.
    repo = StandardNameRepository()
    # Simple sanity: at least one known name present
    assert any(m.name == "magnetic_field" for m in repo.list())
