from copy import copy, deepcopy
import csv
import itertools

import json
import pint
import pydantic
import pytest
import strictyaml as syaml

from imas_standard_names.standard_name import (
    GenericNames,
    ParseJson,
    ParseYaml,
    StandardName,
    StandardNames,
    StandardInput,
)

standard_name_data = {
    "name": "ion_temperature",
    "documentation": "multi-line\ndoc string",
    "units": "A",
    "alias": "",
    "tags": "",
    "options": [],
}


yaml_single = syaml.as_document(
    {
        standard_name_data["name"]: {
            key: standard_name_data[key]
            for key in StandardName.attrs
            if key != "name" and key in standard_name_data
        }
    },
    schema=ParseYaml.schema,
)

yaml_multi = syaml.as_document(
    {
        name: {
            "units": units,
            "documentation": "docs",
            "links": [
                "https://github.com/iterorganization/IMAS-Standard-Names/issues/5",
                "https://github.com/iterorganization/IMAS-Standard-Names/issues/6",
            ],
        }
        for name, units in zip(
            ["plasma_current", "plasma_current_density", "electron_temperature"],
            ["A", "A/m^2", "eV"],
        )
    },
    schema=ParseYaml.schema,
)


def test_standard_name():
    standard_name = StandardName(**standard_name_data)
    for key, value in standard_name.items():
        if value != "":
            assert getattr(standard_name, key) == value


@pytest.mark.parametrize("key", ["alias", "tags", "links"])
def test_standard_name_empty_string(key):
    name = "plasma_current"
    standard_name = StandardName(name=name, documentation="docs", **{key: ""})
    assert key not in standard_name.as_document()[name]


@pytest.mark.parametrize("key", ["tags", "links"])
def test_standard_name_empty_list(key):
    name = "plasma_current"
    standard_name = StandardName(name=name, documentation="docs", **{key: []})
    assert key not in standard_name.as_document()[name]


@pytest.mark.parametrize(
    "data",
    [
        {"tags": "pf_active,equilibrium, tag with white space "},
        {
            "links": "https://github.com/iterorganization/IMAS-Standard-Names/issues/5,"
            "https://github.com/iterorganization/IMAS-Standard-Names/issues/8"
        },
    ],
)
def test_standard_name_lists(data):
    key, value = next(iter(data.items()))
    name = "plasma_current"
    standard_name = StandardName(name=name, documentation="docs", **{key: value})
    assert standard_name.as_document()[name][key] == [
        item.strip() for item in value.split(",")
    ]


@pytest.mark.parametrize("units", ["", "m.s^2"])
def test_standard_name_with_units(units):
    name = "plasma_current"
    standard_name = StandardName(name=name, documentation="docs", units=units)
    assert "units" in standard_name.as_document()[name]
    assert units == standard_name.as_document()[name]["units"]


def test_standard_name_without_units():
    name = "plasma_current"
    standard_name = StandardName(name=name, documentation="docs", units="none")
    assert "units" not in standard_name.as_document()[name]


def test_parse_yaml_without_units():
    standard_name = ParseYaml(
        StandardName(**standard_name_data | {"units": "none"}).as_yaml()
    )[standard_name_data["name"]]
    assert "units" not in standard_name.as_document()[standard_name_data["name"]]


def test_parse_units_error():
    with pytest.raises(ValueError):
        StandardName.parse_units("A / m^2:~P:~F")


@pytest.mark.parametrize(
    "units", ["m/s", "m.s^-1", "meters per second", "meters/second", "m/s:~F"]
)
def test_standard_name_units(units):
    name = "plasma_current"
    standard_name = StandardName(name=name, documentation="docs", units=units)
    assert standard_name.as_document()[name]["units"] == "m.s^-1"


@pytest.mark.parametrize(
    "name",
    ["1st_plasma", "Main_ion_density", "_private", "plasma current", "plasmaCurrent"],
)
def test_name_validator(name):
    with pytest.raises(NameError):
        StandardName(name=name, units="A", documentation="docs")


def test_units_validator():
    with pytest.raises(pydantic.ValidationError):
        StandardName(name="plasma_current", units=1, documentation="docs")


def test_docs_validator():
    with pytest.raises(pydantic.ValidationError):
        StandardName(name="plasma_current", units="A", documentation=None)


def test_alias_validator():
    with pytest.raises(pydantic.ValidationError):
        StandardName(name="plasma_current", units="A", documentation="docs", alias=1)


def test_units_parser():
    assert (
        StandardName(
            name="electron_temperature", units="electron_volt", documentation="docs"
        ).units
        == "eV"
    )


@pytest.mark.parametrize(
    "units,unit_format",
    itertools.product(["eV", "electron_volt", "m/s^2"], ["~P", "P", "D", "~D", "H"]),
)
def test_units_unit_format(units, unit_format):
    standard_name = StandardName(
        **standard_name_data | {"units": f"{units}:{unit_format}"}
    )
    assert standard_name.units == f"{pint.Unit(units):{unit_format}}"


def test_units_parser_error():
    with pytest.raises(pint.errors.UndefinedUnitError):
        StandardName(name="electron_temperature", units="eVv", documentation="docs")


def test_yaml_input():
    standard_name = ParseYaml(yaml_single.as_yaml())[standard_name_data["name"]]
    for key, value in standard_name.items():
        if key == "name" or value == "":
            continue
        assert getattr(standard_name, key) == value


@pytest.mark.parametrize("unit_format", ["~P", "P", "D", "~D", "H", "", None])
def test_yaml_unit_format(unit_format):
    standard_name = ParseYaml(yaml_single.as_yaml(), unit_format=unit_format)[
        standard_name_data["name"]
    ]
    if not unit_format:
        unit_format = "~P"
    assert (
        standard_name.units == f"{pint.Unit(standard_name_data['units']):{unit_format}}"
    )


def test_json_input():
    github_response = json.dumps(standard_name_data)
    standard_name = ParseJson(github_response)[standard_name_data["name"]]
    for key, value in standard_name.items():
        if key == "name" or value == "":
            continue
        assert getattr(standard_name, key) == value


def test_json_name():
    github_response = json.dumps(standard_name_data)
    assert ParseJson(github_response).name == standard_name_data["name"]


def test_yaml_json_equality():
    yaml_standard_name = ParseYaml(yaml_single.as_yaml())[standard_name_data["name"]]
    json_standard_name = ParseJson(json.dumps(standard_name_data)).standard_name
    assert yaml_standard_name == json_standard_name


def test_yaml_roundtrip():
    standard_name = ParseYaml(yaml_multi.as_yaml())
    for key in yaml_multi.as_marked_up():
        assert (
            ParseYaml(standard_name[key].as_yaml())[key]
            == ParseYaml(yaml_multi.as_yaml())[key]
        )


@pytest.fixture()
def standardnames(tmp_path_factory):
    filepath = tmp_path_factory.mktemp("data") / "standardnames.yaml"
    with open(filepath, "w") as f:
        f.write(ParseYaml(yaml_multi.as_yaml()).as_yaml())
    return filepath


def test_standard_name_file_without_suffix(standardnames):
    with pytest.raises(syaml.YAMLValidationError):
        StandardNames(standardnames.with_suffix(""))


def test_standard_name_file(standardnames):
    standard_input = ParseYaml(yaml_multi.as_yaml())
    standard_names = StandardNames(standardnames)
    for key in yaml_multi.as_marked_up():
        assert standard_names[key] == standard_input[key]


def test_file_update(standardnames):
    standard_names = StandardNames(standardnames)
    assert standard_name_data["name"] not in standard_names.data
    standard_names_document = standard_names.data.whole_document()
    github_response = json.dumps(standard_name_data)
    standard_name = ParseJson(github_response).standard_name
    standard_names.update(standard_name)
    assert standard_name_data["name"] in standard_names.data
    assert (
        standard_names[standard_name_data["name"]]
        == ParseJson(github_response).standard_name
    )
    new_standard_names = StandardNames(standardnames)
    assert standard_names.data.whole_document() != standard_names_document
    assert (
        new_standard_names[standard_name_data["name"]]
        == ParseJson(github_response).standard_name
    )


def test_alias_update(standardnames):
    standard_names = StandardNames(standardnames)
    github_response = json.dumps(
        standard_name_data
        | {"name": "another_plasma_current", "alias": "plasma_current"}
    )
    standard_name = ParseJson(github_response).standard_name
    standard_names.update(standard_name)
    assert "another_plasma_current" in standard_names.data


def test_alias_update_error(standardnames):
    standard_names = StandardNames(standardnames)
    github_response = json.dumps(standard_name_data | {"alias": "undefined"})
    standard_name = ParseJson(github_response).standard_name
    with pytest.raises(KeyError):
        standard_names.update(standard_name)


def test_file_update_overwrite_error(standardnames):
    standard_names = StandardNames(standardnames)
    github_response = json.dumps(standard_name_data | {"name": "plasma_current"})
    standard_name = ParseJson(github_response).standard_name
    with pytest.raises(KeyError):
        standard_names.update(standard_name, overwrite=False)


def test_link_update(standardnames):
    standard_names = StandardNames(standardnames)
    assert len(standard_names["plasma_current"].links) == 2
    github_response = json.dumps(
        standard_name_data
        | {
            "name": "plasma_current",
            "links": "https://github.com/iterorganization/IMAS-Standard-Names/issues/7",
        }
    )
    standard_name = ParseJson(github_response).standard_name
    standard_names.update(standard_name, overwrite=True, update_file=False)
    assert len(standard_names["plasma_current"].links) == 3
    assert [
        int(link.split("/")[-1]) for link in standard_names["plasma_current"].links
    ] == [5, 6, 7]


def test_unique_links(standardnames):
    standard_names = StandardNames(standardnames)
    assert len(standard_names["plasma_current"].links) == 2
    github_response = json.dumps(
        standard_name_data
        | {
            "name": "plasma_current",
            "links": "https://github.com/iterorganization/IMAS-Standard-Names/issues/7,"
            "https://github.com/iterorganization/IMAS-Standard-Names/issues/7,"
            "https://github.com/iterorganization/IMAS-Standard-Names/issues/8,"
            "https://github.com/iterorganization/IMAS-Standard-Names/issues/7",
        }
    )
    standard_name = ParseJson(github_response).standard_name
    standard_names.update(standard_name, overwrite=True, update_file=False)
    assert len(standard_names["plasma_current"].links) == 4


@pytest.fixture(scope="session")
def generic_names(tmp_path_factory):
    filepath = tmp_path_factory.mktemp("data") / "generic_names.csv"
    data = [("m^2", "area"), ("A", "current"), ("J", "energy")]
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(["Unit", "Generic Name"])
        writer.writerows(data)
    return GenericNames(filepath)


@pytest.mark.parametrize("name", ["area", "current", "energy"])
def test_is_generic_name(generic_names, name):
    assert name in generic_names


@pytest.mark.parametrize("name", ["plasma_current", "electron_temperature"])
def test_is_not_generic_name(generic_names, name):
    assert name not in generic_names


def test_json_extra_priority_attr(tmp_path):
    filename = tmp_path / "test.json"
    with open(filename, "w") as f:
        json.dump(standard_name_data | {"options": "high priority"}, f)
    StandardInput(filename)[standard_name_data["name"]]


def test_json_roundtrip():
    assert (
        ParseJson(StandardName(**standard_name_data).as_json()).standard_name
        == ParseJson(json.dumps(standard_name_data)).standard_name
    )


def test_standard_name_addition_subtraction():
    standard_names = StandardNames(deepcopy(yaml_single))
    other_standard_names = StandardNames(deepcopy(yaml_multi))
    standard_names += other_standard_names
    standard_names += StandardName(name="plasma_current", documentation="docs")
    standard_names += StandardName(
        name="plasma_volume", documentation="docs"
    ).as_document()
    names = [name.data for name in standard_names.data.keys()]
    assert len(standard_names.data.keys()) == len(names)
    for name in names:
        assert name in standard_names.data
        standard_names -= StandardName(name=name, documentation="other docs")
    assert len(standard_names.data.keys()) == 0


def test_standard_name_difference(standardnames):
    standard_names = StandardNames(standardnames)

    submit_standard_names = deepcopy(standard_names)
    submit_standard_names += StandardName(**standard_name_data).as_document()
    new_standard_names = (
        deepcopy(standard_names) + StandardName(**standard_name_data).as_document()
    )
    new_standard_names -= standard_names
    empty_standard_names = deepcopy(standard_names) - submit_standard_names
    assert len(empty_standard_names.data) == 0

    for key in standard_names.data:
        assert key not in new_standard_names.data

    assert standard_name_data["name"] in new_standard_names.data


def test_standard_name_file_inputs(standardnames):
    standard_names_from_file_str = StandardNames(standardnames.as_posix())
    standard_names_from_file_path = StandardNames(standardnames)
    standard_names_from_yaml_str = StandardNames(
        standard_names_from_file_path.as_yaml()
    )
    standard_names_from_yaml = StandardNames(standard_names_from_file_path.data)

    assert standard_names_from_file_str.data == standard_names_from_file_path.data
    assert standard_names_from_file_str.data == standard_names_from_yaml_str.data
    assert standard_names_from_file_path.data == standard_names_from_yaml.data


def test_deepcopy(standardnames):
    standard_names = StandardNames(standardnames)
    standard_names_copy = copy(standard_names)
    standard_names_deepcopy = deepcopy(standard_names)

    assert standard_names_copy == standard_names
    assert standard_names_deepcopy == standard_names
    standard_names.data["plasma_current"]["units"] = "s"
    assert standard_names_copy == standard_names
    assert standard_names_deepcopy != standard_names
    assert standard_names_deepcopy.data["plasma_current"]["units"] == "A"


def test_filename_setter(standardnames):
    standard_names = StandardNames(standardnames)
    standard_names_deepcopy = deepcopy(standard_names)

    assert standard_names.filename == standardnames
    assert standard_names_deepcopy.filename == standardnames
    standard_names_deepcopy.filename = standardnames.with_suffix(".yml")
    assert standard_names_deepcopy.filename == standardnames.with_suffix(".yml")
    assert standard_names_deepcopy.filename != standard_names.filename


def test_parse_yaml_input_error(standardnames):
    standard_names = StandardNames(standardnames)
    with pytest.raises(TypeError):
        ParseYaml(standard_names.data.as_marked_up())


def test_standard_names_file_input_error(standardnames):
    standard_names = StandardNames(standardnames)
    with pytest.raises(TypeError):
        StandardNames(standard_names.data.as_marked_up())


def test_filename_unset_error(standardnames):
    standard_names = StandardNames(standardnames)
    standard_names_from_yaml = StandardNames(standard_names.as_yaml())
    with pytest.raises(ValueError):
        standard_names_from_yaml.filename


@pytest.mark.parametrize(
    "data",
    [
        {
            "name": "ion_temperature",
            "documentation": "multi-line\ndoc string",
            "units": "A",
            "alias": "",
            "tags": "",
            "links": "",
        },
        {
            "name": "coordinate_label",
            "documentation": "docs",
            "units": "none",
            "alias": "another_coorninate_label",
            "tags": "equilibrium, geometry",
            "links": "link1,https://link2.com",
        },
        {
            "name": "non_dimensional_parameter",
            "documentation": "docs",
            "units": ":F",
            "alias": "same_parameter_with_a_different_name",
            "tags": ["equilibrium", "non-dimensional"],
            "links": ["link1", "https://link2.com"],
        },
    ],
)
def test_standard_name_as_html(data):
    standard_name = StandardName(**data)
    html_output = standard_name.as_html()

    assert "<div" in html_output
    assert "</div>" in html_output
    assert standard_name.name in html_output

    for key, value in standard_name.items():
        if value and value != "none":
            if key == "documentation":
                assert key in html_output
            else:
                assert key.capitalize() in html_output
            if isinstance(value, str):
                assert value in html_output
            else:
                assert all(item in html_output for item in value)
            if key == "links":
                assert isinstance(value, list)
                assert all(
                    "href" in html_output
                    for link in value
                    if link.startswith(("http://", "https://"))
                )

        else:
            assert key.capitalize() not in html_output


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])
