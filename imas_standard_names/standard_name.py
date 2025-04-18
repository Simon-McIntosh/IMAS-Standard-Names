from dataclasses import dataclass, field, InitVar
from functools import cached_property
import json
from pathlib import Path
from typing import ClassVar

import markdown
import numpy as np
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
        """Return units validated and formatted with pint."""
        match units.split(":"):
            case [str(units), str(unit_format)]:
                pass
            case [str(units)]:
                unit_format = "~F"
            case _:
                raise ValueError(
                    f"Invalid units format: {units}. "
                    "Expected 'units' or 'units:format'."
                )
        if units == "none":
            return units
        if "L" in unit_format:  # LaTeX format
            return f"$`{pint.Unit(units):{unit_format}}`$"
        return f"{pint.Unit(units):{unit_format}}"

    @pydantic.field_validator("tags", "links", mode="after")
    @classmethod
    def parse_list(cls, value: str | list[str]) -> str | list[str]:
        """Return list of comma separated strings."""
        if value == "" or isinstance(value, list):
            return value
        return [item.strip() for item in value.split(",")]

    def as_dict(self) -> dict:
        """Return a dictionary representation of the StandardName instance."""
        return {"name": self.name} | dict(self.items())

    def items(self):
        """Return a dictionary of attrs and their values."""
        return {attr: getattr(self, attr) for attr in self.attrs}.items()

    def as_document(self) -> syaml.YAML:
        """Return standard name as a YAML document."""
        data = {
            key: value
            for key, value in self.items()
            if (key == "units" and value != "none")
            or (key != "units" and value != [] and value != "")
        }
        return syaml.as_document({self.name: data}, schema=ParseYaml.schema)

    def as_yaml(self) -> str:
        """Return standard name as YAML string."""
        return self.as_document().as_yaml()

    def as_json(self):
        """Return standard name as JSON string."""
        return json.dumps(
            self.as_document().as_marked_up()[self.name] | {"name": self.name}
        )

    def as_html(self) -> str:
        """Return standard name as HTML string.

        Creates an HTML representation of the standard name with all its
        attributes formatted for documentation or display purposes.
        """
        html = f"<div class='standard-name' id='{self.name}'>\n"
        html += f"  <h2>{self.name}</h2>\n"

        # Documentation
        html += "  <div class='documentation'>\n"
        html += f"    {markdown.markdown(self.documentation)}\n"
        html += "  </div>\n"

        # Create details table for other attributes
        html += "  <table class='details'>\n"

        # Units (if not 'none')
        if self.units != "none":
            html += "    <tr>\n"
            html += "      <th>Units</th>\n"
            html += f"      <td>{self.units}</td>\n"
            html += "    </tr>\n"

        # Alias (if present)
        if self.alias:
            html += "    <tr>\n"
            html += "      <th>Alias</th>\n"
            html += f"      <td><a href='#{self.alias}'>{self.alias}</a></td>\n"
            html += "    </tr>\n"

        # Tags (if present)
        if isinstance(self.tags, list) and self.tags:
            tags_html = ", ".join(
                [f"<span class='tag'>{tag}</span>" for tag in self.tags]
            )
            html += "    <tr>\n"
            html += "      <th>Tags</th>\n"
            html += f"      <td>{tags_html}</td>\n"
            html += "    </tr>\n"

        # Links (if present)
        if isinstance(self.links, list) and self.links:
            links_html = "<ul>\n"
            for link in self.links:
                if link.startswith(("http://", "https://")):
                    links_html += f"        <li><a href='{link}'>{link}</a></li>\n"
                else:
                    links_html += f"        <li>{link}</li>\n"
            links_html += "      </ul>"
            html += "    <tr>\n"
            html += "      <th>Links</th>\n"
            html += f"      <td>{links_html}</td>\n"
            html += "    </tr>\n"

        html += "  </table>\n"
        html += "</div>\n"

        return html


@dataclass
class ParseYaml:
    """Ingest IMAS Standard Names with a YAML schema."""

    input_: InitVar[str | syaml.YAML]
    data: syaml.YAML = field(init=False, repr=False)
    unit_format: str | None = None

    schema: ClassVar = syaml.EmptyDict() | syaml.MapPattern(
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

    def __post_init__(self, input_: str | syaml.YAML):
        """Load yaml data."""
        match input_:
            case str():
                self.data = syaml.load(input_, self.schema)
            case syaml.YAML():
                self.data = input_
            case _:
                raise TypeError(
                    f"Invalid input type: {type(input_)}. Expected str or YAML."
                )

    def _append_unit_format(self, data: syaml.YAML):
        """Append unit formatter to units string."""
        if self.unit_format:
            data["units"] = data["units"].split(":")[0] + f":{self.unit_format}"

    def __getitem__(self, standard_name: str) -> StandardName:
        """Return StandardName instance for the requested standard name."""
        data = self.data[standard_name].as_marked_up()
        if "units" in data:
            self._append_unit_format(data)
        return StandardName(name=standard_name, **data)

    def as_yaml(self) -> str:
        """Return yaml data as string."""
        yaml_data = ""
        for name in self.data:
            yaml_data += self[str(name)].as_yaml()
        return yaml_data

    def _as_document(self, other) -> syaml.YAML:
        """Return other as yaml document."""
        match other:
            case StandardName():
                other = other.as_document()
            case StandardNameFile():
                other = other.data
            case syaml.YAML():
                pass
        return other

    def __add__(self, other: syaml.YAML | StandardName) -> "ParseYaml":
        """Add content of other to self, overriding existing keys."""
        other = self._as_document(other)
        for key, value in other.data.items():
            # append issue links to existing list
            if key in self.data:
                links = self.data.data[key].get("links", []) + value.get("links", [])
                value["links"] = np.unique(links).tolist()
                if not value["links"]:
                    value["links"] = ""
            self.data[key] = value
        return self

    def __iadd__(self, other):
        """Add content of other to self, overriding existing keys."""
        return self.__add__(other)

    def __sub__(self, other):
        """Remove content of other from self."""
        other = self._as_document(other)
        for key in other.data:
            if key in self.data:
                del self.data[key]
        return self

    def __isub__(self, other):
        """Remove content of other from self."""
        return self.__sub__(other)


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

    input_: InitVar[str | Path | syaml.YAML]
    _filename: Path | None = field(init=False, repr=False)

    def __post_init__(self, input_: str | Path | syaml.YAML):
        """Load standard name data from yaml file."""
        match input_:
            case "":
                pass
            case str() if self._is_yaml(input_):
                self._filename = None
            case str() | Path():
                self._filename = Path(input_)
                with open(self.filename, "r") as f:
                    input_ = f.read()
            case syaml.YAML():
                self._filename = None
            case _:
                raise TypeError(
                    f"Invalid input type: {type(input_)}. Expected str, Path, or YAML."
                )
        if input_ == "":
            self.data = syaml.as_document({}, schema=self.schema)
            return
        super().__post_init__(input_)

    @staticmethod
    def _is_yaml(input_: str) -> bool:
        """Return True if str looks like YAML content."""
        return any(c in input_ for c in ["\n", ":", "-"]) and not Path(input_).exists()

    @property
    def filename(self) -> Path:
        """Return standardnames yaml file path."""
        if self._filename is None:
            raise ValueError("Data input from YAML. No filename provided.")
        if self._filename.suffix in [".yml", ".yaml"]:
            return self._filename
        return self._filename.with_suffix(".yaml")

    @filename.setter
    def filename(self, value: str | Path):
        """Set standard names yaml file path."""
        self._filename = Path(value)

    def update(
        self,
        standard_name: StandardName,
        overwrite: bool = False,
        update_file: bool = True,
    ):
        """Add json data to self and update standard names file."""
        if not overwrite:  # check for existing standard name
            try:
                assert standard_name.name not in self.data
            except AssertionError:
                raise KeyError(
                    f"The proposed standard name **{standard_name.name}** "
                    f"is already present in the {self.filename} file.\n\n"
                    # "with the following content:"
                    # f"\n\n{self[standard_name.name].as_html()}\n\n"
                    "Mark the :white_check_mark: **overwrite** checkbox "
                    "to overwrite this standard name."
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
        if update_file:
            with open(self.filename.with_name("submission.yml"), "w") as f:
                f.write(standard_name.as_yaml())
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
        """Check if name is included in the generic standard name list."""
        return name in self.names

    def check(self, standard_name: str) -> None:
        """Check proposed standard name against generic name list."""
        if standard_name in self:
            raise KeyError(
                f"The proposed standard name **{standard_name}** "
                "is a generic name."
                f"\n\n{self.data.to_markdown()}.\n\n"
                ":card_file_box: Please propose a different name. See [guidelines](https://github.com/iterorganization/IMAS-Standard-Names/blob/main/docs/guidelines.md) for advice on Standard Name construction."
            )


if __name__ == "__main__":  # pragma: no cover
    standard_names = StandardNameFile("")
