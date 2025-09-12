from dataclasses import dataclass, field, InitVar
from functools import cached_property
import json
from pathlib import Path
from typing import ClassVar
from enum import Enum, StrEnum

import markdown
import numpy as np
import pandas
import pydantic
import strictyaml as syaml
import yaml

from imas_standard_names import pint


class Kind(StrEnum):
    scalar = "scalar"
    vector = "vector"
    derived_scalar = "derived_scalar"
    derived_vector = "derived_vector"


class Status(StrEnum):
    draft = "draft"
    accepted = "accepted"
    deprecated = "deprecated"
    experimental = "experimental"
    superseded = "superseded"


class Frame(StrEnum):
    cylindrical_r_tor_z = "cylindrical_r_tor_z"
    cartesian_x_y_z = "cartesian_x_y_z"
    spherical_r_theta_phi = "spherical_r_theta_phi"
    toroidal_R_phi_Z = "toroidal_R_phi_Z"
    flux_surface = "flux_surface"


class StandardName(pydantic.BaseModel):
    """Strict Standard Name model."""

    model_config = pydantic.ConfigDict(use_enum_values=True)

    # Required core
    name: str
    kind: Kind
    status: Status
    unit: str = "none"
    description: str

    # Optional extended
    documentation: str = ""
    parent_scalar: str = ""
    parent_vector: str = ""
    frame: Frame | None = None
    components: dict[str, str] | None = None
    tags: list[str] = []
    alias: str = ""

    # Structured governance / lifecycle fields
    constraints: list[
        str
    ] = []  # Physical or mathematical constraints (atomic statements)
    validity_domain: str = ""  # Short phrase or sentence describing domain of validity
    deprecates: str = ""  # Name this entry deprecates (if any)
    superseded_by: str = ""  # Forward pointer if deprecated/superseded

    attrs: ClassVar[list[str]] = [
        "kind",
        "status",
        "unit",
        "description",
        "documentation",
        "parent_scalar",
        "parent_vector",
        "frame",
        "components",
        "tags",
        "alias",
        "constraints",
        "validity_domain",
        "deprecates",
        "superseded_by",
    ]

    @pydantic.model_validator(mode="after")
    def validate_relationships(self) -> "StandardName":
        errors: list[str] = []
        name = self.name

        def pattern(p: str) -> bool:
            return name.startswith(p)

        is_gradient = pattern("gradient_of_")
        is_time_derivative = pattern("time_derivative_of_")
        is_magnitude = pattern("magnitude_of_")
        # Combined patterns implying derivation chains
        derived_from_scalar = is_gradient or (is_time_derivative and not is_gradient)

        # Vectors must have frame and components (allow empty dict only for placeholder under strict? -> disallow empty)
        if self.kind in {Kind.vector, Kind.derived_vector}:
            if self.frame is None:
                errors.append("frame is required for vector or derived_vector kinds")
            if self.components is None or len(self.components) == 0:
                errors.append("components mapping required for vector/derived_vector")

        # parent_scalar required when vector derived from scalar (gradient/time derivative of scalar field)
        if self.kind in {Kind.vector, Kind.derived_vector} and derived_from_scalar:
            if not self.parent_scalar and not self.parent_vector:
                errors.append(
                    "parent_scalar (or parent_vector if deriving from vector) required for derived vector"
                )

        # parent_vector required for scalar magnitude_of_ or component-of vector patterns
        if self.kind in {Kind.scalar, Kind.derived_scalar} and (
            is_magnitude or "component_of_" in name
        ):
            if not self.parent_vector:
                errors.append("parent_vector required for magnitude/component scalar")

        # Disallow both parent_scalar and parent_vector simultaneously unless kind is derived_vector
        if (
            self.parent_scalar
            and self.parent_vector
            and self.kind not in {Kind.derived_vector}
        ):
            errors.append(
                "only one of parent_scalar or parent_vector should be set (except for derived_vector)"
            )

        if errors:
            raise ValueError("; ".join(errors))
        return self

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

    @pydantic.field_validator("unit", mode="after")
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

    @pydantic.field_validator("tags", "constraints", mode="after")
    @classmethod
    def parse_list(cls, value):  # type: ignore[override]
        """Normalize list-like fields.

        - If already a list -> return as-is.
        - If empty / None -> return [] (simplifies downstream handling).
        - If string -> split on commas.
        """
        if isinstance(value, list):
            return value
        if value in ("", None):
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return []

    def as_dict(self) -> dict:
        """Return a dictionary representation of the StandardName instance."""
        return {"name": self.name} | dict(self.items())

    def items(self):
        """Return a dictionary of attrs and their values."""
        return {attr: getattr(self, attr) for attr in self.attrs}.items()

    def as_document(self) -> syaml.YAML:
        """Return standard name as a YAML document."""
        data = {}
        for key, value in self.items():
            # Skip empty / default values
            if key == "unit" and value == "none":
                continue
            if value in ("", [], None):
                continue
            # Normalize list-like serialization
            if key in {"tags"} and isinstance(value, list) and not value:
                continue
            data[key] = value
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

        # Description (short)
        if self.description:
            html += "  <div class='description'>\n"
            html += f"    {markdown.markdown(self.description)}\n"
            html += "  </div>\n"

        # Documentation (extended)
        if self.documentation:
            html += "  <div class='documentation'>\n"
            html += f"    {markdown.markdown(self.documentation)}\n"
            html += "  </div>\n"

        # Create details table for other attributes
        html += "  <table class='details'>\n"

        # Description row (duplicate of block above, provides label in table)
        if self.description:
            html += "    <tr>\n"
            html += "      <th>Description</th>\n"
            html += f"      <td>{markdown.markdown(self.description)}</td>\n"
            html += "    </tr>\n"

        # Unit (if not 'none')
        if self.unit != "none":
            html += "    <tr>\n"
            html += "      <th>Unit</th>\n"
            html += f"      <td>{self.unit}</td>\n"
            html += "    </tr>\n"

        # Optional metadata rows
        for meta_key in [
            ("Kind", self.kind.value if isinstance(self.kind, Enum) else self.kind),
            (
                "Status",
                self.status.value if isinstance(self.status, Enum) else self.status,
            ),
            ("Frame", self.frame.value if isinstance(self.frame, Enum) else self.frame),
            ("Parent Scalar", self.parent_scalar),
            ("Parent Vector", self.parent_vector),
        ]:
            label, value = meta_key
            if value:
                html += "    <tr>\n"
                html += f"      <th>{label.replace('_', ' ').title()}</th>\n"
                html += f"      <td>{value}</td>\n"
                html += "    </tr>\n"

        # Components / vector components
        if self.components:
            comp_repr = self.components
            comp_html = (
                "<ul>"
                + "".join(
                    f"<li><strong>{k}</strong>: {v}</li>" for k, v in comp_repr.items()
                )
                + "</ul>"
            )
            html += "    <tr>\n"
            html += "      <th>Components</th>\n"
            html += f"      <td>{comp_html}</td>\n"
            html += "    </tr>\n"
        # Constraints list
        if isinstance(self.constraints, list) and self.constraints:
            constraints_html = (
                "<ul>"
                + "".join(f"<li>{markdown.markdown(c)}</li>" for c in self.constraints)
                + "</ul>"
            )
            html += "    <tr>\n"
            html += "      <th>Constraints</th>\n"
            html += f"      <td>{constraints_html}</td>\n"
            html += "    </tr>\n"

        # Validity domain
        if self.validity_domain:
            html += "    <tr>\n"
            html += "      <th>Validity Domain</th>\n"
            html += f"      <td>{markdown.markdown(self.validity_domain)}</td>\n"
            html += "    </tr>\n"

        # Deprecation / supersession metadata
        if self.deprecates:
            html += "    <tr>\n"
            html += "      <th>Deprecates</th>\n"
            html += f"      <td>{self.deprecates}</td>\n"
            html += "    </tr>\n"
        if self.superseded_by:
            html += "    <tr>\n"
            html += "      <th>Superseded By</th>\n"
            html += f"      <td>{self.superseded_by}</td>\n"
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
                "kind": syaml.Str(),
                "status": syaml.Str(),
                "unit": syaml.Str(),
                "description": syaml.Str(),
                syaml.Optional("documentation"): syaml.Str(),
                syaml.Optional("parent_scalar"): syaml.Str(),
                syaml.Optional("parent_vector"): syaml.Str(),
                syaml.Optional("frame"): syaml.Str(),
                syaml.Optional("components"): syaml.MapPattern(
                    syaml.Str(), syaml.Str()
                ),
                syaml.Optional("tags"): syaml.Str() | syaml.Seq(syaml.Str()),
                syaml.Optional("alias"): syaml.Str(),
                syaml.Optional("constraints"): syaml.Str() | syaml.Seq(syaml.Str()),
                syaml.Optional("validity_domain"): syaml.Str(),
                syaml.Optional("deprecates"): syaml.Str(),
                syaml.Optional("superseded_by"): syaml.Str(),
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
        # Defensive: strictyaml Document exposes .data (an OrderedDict-like mapping)
        other_map = getattr(other, "data", {})  # type: ignore[arg-type]
        if not isinstance(other_map, dict):  # pragma: no cover - defensive
            return self
        for key, value in other_map.items():
            # Merge links uniquely if both sides have them
            if key in self.data:
                existing = self.data.data.get(key, {})  # type: ignore[index]
                if isinstance(existing, dict) and isinstance(value, dict):
                    existing_links = existing.get("links", [])
                    new_links = value.get("links", [])
                    if not isinstance(existing_links, list):
                        existing_links = []
                    if not isinstance(new_links, list):
                        new_links = []
                    merged = np.unique(existing_links + new_links).tolist()
                    if merged:
                        value["links"] = merged
                    elif "links" in value:
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

    def __post_init__(self, input_: str | syaml.YAML):  # type: ignore[override]
        """Load JSON data (string), extract standard name and convert to YAML.

        If a YAML object is passed (edge case) we defer to parent implementation.
        """
        if isinstance(input_, syaml.YAML):  # pragma: no cover - fallback
            return super().__post_init__(input_)
        response = json.loads(str(input_))
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

    input_: InitVar[str | syaml.YAML]
    issue_link: InitVar[str] = ""

    def __post_init__(self, input_: str | syaml.YAML, issue_link: str):  # type: ignore[override]
        """Load JSON data from file path (string) and attach issue link."""
        self.filename = Path(str(input_)).with_suffix(".json")
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
                        yaml_text = self._build_directory_yaml(path)
                        # Recursively parse the gathered YAML
                        self.__post_init__(yaml_text)
                        return
                    if path.is_file():
                        self._dirname = path.parent
                        self._origin_file = path
                        with open(path, "r", encoding="utf-8") as f:
                            yaml_text = f.read()
                        self.__post_init__(yaml_text)
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

    def _build_directory_yaml(self, dirname: Path) -> str:
        """Build and return a single concatenated YAML string from all *.yml|*.yaml files under dirname.

        Performs:
        - Discovery of per-file standard name YAML files.
        - Parsing and schema validation (raising on unexpected fields).
        - Construction of the aggregated multi-document YAML text.
        """
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
            # Detect any unexpected / unmapped fields and raise
            # so users get explicit feedback.
            unexpected = [
                k for k in parsed.keys() if k not in StandardName.attrs and k != "name"
            ]
            if unexpected:
                raise ValueError(
                    "Unexpected field(s) "
                    f"{unexpected} in file {file}. These are not part of the StandardName schema: "
                    f"{StandardName.attrs}"
                )
            yaml_docs.append(
                syaml.as_document({name: parsed}, schema=ParseYaml.schema).as_yaml()
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

        When persisting, write two files:
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
    standard_names = StandardNames("resources/standard_names")

    print(standard_names)
