from imas_standard_names.schema import create_standard_name
from imas_standard_names.catalog.sqlite_rw import CatalogReadWrite
from imas_standard_names.services import row_to_model


def test_sqlite_catalog_insert_search_get():
    cat = CatalogReadWrite()
    m = create_standard_name(
        {
            "name": "electron_temperature",
            "kind": "scalar",
            "description": "Electron temperature.",
            "unit": "eV",
            "status": "active",
        }
    )
    cat.insert(m)
    assert cat.get("electron_temperature") is not None
    results = cat.search("electron_temperature")
    assert "electron_temperature" in results
    # round-trip conversion
    raw_row = cat.conn.execute(
        "SELECT * FROM standard_name WHERE name=?", ("electron_temperature",)
    ).fetchone()
    model2 = row_to_model(cat.conn, raw_row)
    assert model2.name == m.name


def test_sqlite_catalog_delete():
    cat = CatalogReadWrite()
    m = create_standard_name(
        {
            "name": "ion_temperature",
            "kind": "scalar",
            "description": "Ion temperature.",
            "unit": "eV",
        }
    )
    cat.insert(m)
    assert cat.get("ion_temperature") is not None
    cat.delete("ion_temperature")
    assert cat.get("ion_temperature") is None
