import csv
from imas_standard_names.generic_names import GenericNames


def test_generic_names_membership(tmp_path):
    csv_path = tmp_path / "generic_names.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Unit", "Generic Name"])
        writer.writerows([["m^2", "area"], ["A", "current"], ["J", "energy"]])
    g = GenericNames(csv_path.as_posix())
    assert "area" in g and "plasma_current" not in g
