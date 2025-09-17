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
            case StandardNames():
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
class StandardNames(ParseYaml):
    """Manage the project's standard names stored as individual YAML files.

    The project stores each standard name in a separate YAML file under a
    directory tree. This class scans a directory (recursively) collecting all
    standard name YAML documents into a single strictyaml document.
    """

    _dirname: Path | None = field(init=False, repr=False, default=None)
    _origin_file: Path | None = field(init=False, repr=False, default=None)

    def __post_init__(self, input_: str | syaml.YAML | Path):
        """Load standard name data from directory, file, or raw YAML content."""
        match input_:
            case "":
                self.data = syaml.as_document({}, schema=self.schema)
                return
            case syaml.YAML():
                self._dirname = None
                self._origin_file = None
                super().__post_init__(input_)
                return
            case str() if self._is_yaml_string(input_):
                self._dirname = None
                self._origin_file = None
                super().__post_init__(input_)
                return
            case str() | Path():
                path = Path(input_)
                if path.exists():
                    if path.is_dir():
                        self._dirname = path
                        self._origin_file = None
                        yaml_text = self._gather_directory_yaml(path)
                        # Recursively parse the gathered YAML
                        self.__post_init__(yaml_text)
                        return
                    if path.is_file():
                        self._dirname = path.parent
                        self._origin_file = path
                        with open(path, "r", encoding="utf-8") as f:
                            yaml_text = f.read()
                        super().__post_init__(yaml_text)
                        return
                # Non-existent path or not a file/dir: treat as YAML string
                self._dirname = None
                self._origin_file = None
                super().__post_init__(str(path))
                return
            case _:
                raise TypeError(
                    f"Invalid input type: {type(input_)}. Expected str, Path, or YAML."
                )

    @staticmethod
    def _is_yaml_string(candidate: str) -> bool:
        """Return True if string resembles YAML content (and not an existing path)."""
        return (
            any(c in candidate for c in ["\n", ":", "-"])
            and not Path(candidate).exists()
        )

    def _gather_directory_yaml(self, dirname: Path) -> str:
        """Return concatenated YAML from all *.yml|*.yaml files under dirname."""
        yaml_docs: list[str] = []
        for file in sorted(dirname.rglob("*.yml")) + sorted(dirname.rglob("*.yaml")):
            with open(file, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if not content:
                continue
            # Each individual file may either be a single mapping with a top-level
            # name key (new per-file schema) or the legacy {name: {...}} structure.
            try:
                parsed = yaml.safe_load(content)
            except Exception as exc:  # pragma: no cover - defensive
                raise ValueError(f"Failed parsing YAML file {file}: {exc}") from exc

            if not isinstance(parsed, dict) or "name" not in parsed:
                # Assume legacy structure already in expected format.
                yaml_docs.append(content if content.endswith("\n") else content + "\n")
                continue

            # Convert per-file schema to existing aggregated schema {name: attrs}
            name = parsed.pop("name")
            # Map new field names to existing schema keys when possible.
            # 'description' in new files corresponds to 'documentation'.
            if "description" in parsed and "documentation" not in parsed:
                parsed["documentation"] = parsed.pop("description")
            # Normalise unit key -> units
            if "unit" in parsed and "units" not in parsed:
                parsed["units"] = parsed.pop("unit")
            # Remove fields not currently modeled; could be stored later if needed.
            filtered = {
                k: v
                for k, v in parsed.items()
                if k in StandardName.attrs and k != "name" and v not in (None, "")
            }
            yaml_docs.append(
                syaml.as_document({name: filtered}, schema=ParseYaml.schema).as_yaml()
            )
        return "".join(yaml_docs)

    @property
    def dirname(self) -> Path | None:
        """Return directory containing standard name yaml files, or None."""
        return getattr(self, "_dirname", None)

    @dirname.setter
    def dirname(self, value: str | Path):
        self._dirname = Path(value)

    @property
    def origin_file(self) -> Path | None:
        """Return origin file path, or None."""
        return getattr(self, "_origin_file", None)

    @origin_file.setter
    def origin_file(self, value: str | Path):
        self._origin_file = Path(value)

    def update(
        self,
        standard_name: StandardName,
        overwrite: bool = False,
        update_file: bool = True,
    ):
        """Add or update a StandardName and optionally persist to per-file YAML.

        Behaviour mirrors previous single-file version. When persisting, write
        two files:
        - submission.yml (single-name document for review pipelines)
        - <dirname>/<standard_name>.yml (canonical per-name file)
        """
        if not overwrite and standard_name.name in self.data:
            raise KeyError(
                f"The proposed standard name **{standard_name.name}** is already present.\n\n"
                "Mark the :white_check_mark: **overwrite** checkbox to overwrite this standard name."
            )
        if standard_name.alias and standard_name.alias not in self.data:
            raise KeyError(
                f"The proposed alias **{standard_name.alias}** is not present in the collection."
            )

        self += standard_name.as_document()

        if update_file:
            # Always write submission.yml if directory known
            if self._dirname is not None:  # type: ignore[attr-defined]
                submission_path = self._dirname / "submission.yml"  # type: ignore[attr-defined]
                with open(submission_path, "w", encoding="utf-8") as f:
                    f.write(standard_name.as_yaml())
                # Per-name file (directory mode)
                name_file = self._dirname / f"{standard_name.name}.yml"  # type: ignore[attr-defined]
                with open(name_file, "w", encoding="utf-8") as f:
                    f.write(standard_name.as_yaml())
            # Backwards compatibility: if originally from a single file, refresh it
            if self._origin_file is not None:  # type: ignore[attr-defined]
                with open(self._origin_file, "w", encoding="utf-8") as f:  # type: ignore[attr-defined]
                    f.write(self.data.as_yaml())

    # Backwards compatibility helpers (some tests expect .filename behaviour)
    @property
    def filename(self) -> Path:  # pragma: no cover - backward compatibility
        if self._origin_file is None:
            raise ValueError(
                "Data input from YAML string or directory. No filename provided."
            )
        return self._origin_file

    @filename.setter  # pragma: no cover - transitional
    def filename(self, value):  # noqa: D401
        path = Path(value)
        self._origin_file = path
        self._dirname = path.parent


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
    standard_names = StandardNames("")

    print(standard_names)
