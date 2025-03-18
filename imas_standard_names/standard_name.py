from dataclasses import dataclass, field, InitVar
from functools import cached_property
import json
from pathlib import Path
from typing import ClassVar

import pandas
import pydantic
import strictyaml as syaml
import yaml

from imas_standard_names import pint


class StandardName(pydantic.BaseModel):
    name: str
    documentation: str
    units: str = "none"
    alias: str = ""
    tags: str | list[str] = ""
    links: str | list[str] = ""

    attrs: ClassVar[list[str]] = [
        "documentation",
        "units",
        "alias",
        "tags",
        "links",
    ]

    @pydantic.field_validator("name", mode="after")
    @classmethod
    def validate_standard_name(cls, name: str) -> str:
        """Validate name against IMAS standard name ruleset."""
        try:
            assert name.islower()  # Standard names are lowercase
            assert name[0].isalpha()  # Standard names start with a letter
            assert " " not in name  # Standard names do not contain whitespace
        except AssertionError:
            raise NameError(
                f"The proposed Standard Name **{name}** is *not* valid."
                "\n\nStandard names must:\n"
                "- be lowercase;\n"
                "- start with a letter;\n"
                "- and not contain whitespace."
            )
        return name

    @pydantic.field_validator("units", mode="after")
    @classmethod
    def parse_units(cls, units: str) -> str:
        """Return units validated and formated with pint"""
        match units.split(":"):
            case [str(units), str(unit_format)]:
                pass
            case [str(units)]:
                unit_format = "~F"
        if units == "none":
            return units
        if "L" in unit_format:  # LaTeX format
            return f"$`{pint.Unit(units):{unit_format}}`$"
        return f"{pint.Unit(units):{unit_format}}"

    @pydantic.field_validator("tags", "links", mode="after")
    @classmethod
    def parse_list(cls, value: str | list[str]) -> str | list[str]:
        """Return list of comma seperated strings."""
        if value == "" or isinstance(value, list):
            return value
        return [item.strip() for item in value.split(",")]

    def as_document(self) -> syaml.representation.YAML:
        """Return standard name as a YAML document."""
        data = {
            key: value
            for key, value in self.items()
            if (key == "units" and value != "none")
            or (key != "units" and value != [] and value != "")
        }
        syaml.as_document({self.name: data}, schema=ParseYaml.schema)
        return syaml.as_document({self.name: data}, schema=ParseYaml.schema)

    def as_yaml(self) -> str:
        """Return standard name as YAML string."""
        return self.as_document().as_yaml()

    def as_json(self):
        """Return standard name as JSON string."""
        return json.dumps(
            self.as_document().as_marked_up()[self.name] | {"name": self.name}
        )

    def items(self):
        """Return key-value pairs with keys defined by self.attrs."""
        return {attr: getattr(self, attr) for attr in self.attrs}.items()


@dataclass
class ParseYaml:
    """Ingest IMAS Standard Names with a YAML schema."""

    input_: InitVar[str]
    data: syaml.representation.YAML = field(init=False, repr=False)
    unit_format: str | None = None

    schema: ClassVar = syaml.MapPattern(
        syaml.Str(),
        syaml.Map(
            {
                "documentation": syaml.Str(),
                syaml.Optional("units"): syaml.Str(),
                syaml.Optional("alias"): syaml.Str(),
                syaml.Optional("tags"): syaml.Str() | syaml.Seq(syaml.Str()),
                syaml.Optional("links"): syaml.Str() | syaml.Seq(syaml.Str()),
                syaml.Optional("options"): syaml.EmptyList() | syaml.Seq(syaml.Str()),
            }
        ),
    )

    def __post_init__(self, input_: str):
        """Load yaml data."""
        self.data = syaml.load(input_, self.schema)

    def _append_unit_format(
        self, data: syaml.representation.YAML
    ) -> syaml.representation.YAML:
        """Append unit formatter to units string."""
        if self.unit_format:
            data["units"] = data["units"].split(":")[0] + f":{self.unit_format}"
        return data

    def __getitem__(self, standard_name: str) -> StandardName:
        """Return StandardName instance for the requested standard name."""
        data = self._append_unit_format(self.data[standard_name].as_marked_up())
        return StandardName(name=standard_name, **data)

    def as_yaml(self) -> str:
        """Return yaml data as string."""
        yaml_data = ""
        for name in self.data:
            yaml_data += self[str(name)].as_yaml()
        return yaml_data


@dataclass
class ParseJson(ParseYaml):
    """Process single JSON GitHub issue response as a YAML schema."""

    name: str = field(init=False)

    def __post_init__(self, input_: str):
        """Load JSON data, extract standard name and convert to YAML."""
        response = json.loads(input_)
        response = {
            key: "" if value == [] else value
            for key, value in response.items()
            if value
        }
        self.name = response.pop("name")
        yaml_data = yaml.dump({self.name: response}, default_flow_style=False)
        super().__post_init__(yaml_data)

    @property
    def standard_name(self) -> StandardName:
        """Return StandardName instance for input JSON data."""
        return self[self.name]


@dataclass
class StandardInput(ParseJson):
    """Process standard name input from a GitHub issue form."""

    input_: InitVar[str | Path]
    issue_link: InitVar[str] = ""

    def __post_init__(self, input_: str | Path, issue_link: str):
        """Load JSON data and Format Overwrite flag."""
        self.filename = Path(input_).with_suffix(".json")
        with open(self.filename, "r") as f:
            json_data = f.read()
        data = json.loads(json_data)
        data["links"] = issue_link
        # filter attributes to match StandardName dataclass
        data = {
            attr: data[attr]
            for attr in list(StandardName.__annotations__)
            if attr in data
        }
        super().__post_init__(json.dumps(data))


@dataclass
class StandardNameFile(ParseYaml):
    """Manage the project's standard name file."""

    input_: InitVar[str | Path]

    def __post_init__(self, input_: str | Path):
        """Load standard name data from yaml file."""
        self._filename = Path(input_)
        with open(self.filename, "r") as f:
            yaml_data = syaml.load(f.read(), self.schema)
        super().__post_init__(yaml_data.as_yaml())

    @property
    def filename(self) -> Path:
        """Return standardnames yaml file path."""
        if self._filename.suffix in [".yml", ".yaml"]:
            return self._filename
        return self._filename.with_suffix(".yaml")

    def __add__(self, other):
        """Add content of other to self, overiding existing keys."""
        for key, value in other.data.items():
            # append issue links to existing list
            if key in self.data:
                value["links"] = self.data.data[key].get("links", "") + value.get(
                    "links", ""
                )
            self.data[key] = value
        return self

    def __iadd__(self, other):
        """Add content of other to self, overiding existing keys."""
        return self.__add__(other)

    def update(self, standard_name: StandardName, overwrite: bool = False):
        """Add json data to self and update standard names file."""
        if not overwrite:  # check for existing standard name
            try:
                assert standard_name.name not in self.data
            except AssertionError:
                raise KeyError(
                    f"The proposed standard name **{standard_name.name}** "
                    f"is already present in {self.filename} "
                    "with the following content:"
                    f"\n\n{self[standard_name.name].as_yaml()}\n\n"
                    "Mark the **overwrite** checkbox to overwrite this standard name."
                )
        if standard_name.alias:
            try:
                assert standard_name.alias in self.data
            except AssertionError:
                raise KeyError(
                    f"The proposed alias **{standard_name.alias}** "
                    f"is not present in {self.filename}."
                )
        self += standard_name.as_document()
        with open(self.filename, "w") as f:
            f.write(self.data.as_yaml())


@dataclass
class GenericNames:
    """Manage generic standard names via a csv file."""

    input_: InitVar[str]
    data: pandas.DataFrame = field(init=False, repr=False)

    def __post_init__(self, input_: str):
        """Load csv data."""
        with open(input_, "r", newline="") as f:
            self.data = pandas.read_csv(f)

    @cached_property
    def names(self) -> list[str]:
        """Return generic standard name list."""
        return self.data["Generic Name"].tolist()

    def __contains__(self, name: str) -> bool:
        """Check if name is inlcuded the the generic standard name list."""
        return name in self.names

    def check(self, standard_name: str) -> None:
        """Check proposed standard name against generic name list."""
        if standard_name in self:
            raise KeyError(
                f"The proposed standard name **{standard_name}** "
                "is a generic name."
                f"\n\n{self.data.to_markdown()}.\n\n"
                "Please choose a different name."
            )


if __name__ == "__main__":  # pragma: no cover
    standard_names = StandardNameFile("../standardnames.yml")
