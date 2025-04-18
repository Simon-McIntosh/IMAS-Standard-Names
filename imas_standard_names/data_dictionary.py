from dataclasses import dataclass
from functools import cached_property
import textwrap


import imas


@dataclass
class IdsIssue:
    name: str
    path: str
    overwrite: bool = False

    @cached_property
    def metadata(self):
        """Return metadata for IDS attribute at path."""
        return imas.IDSFactory().new(self.name).metadata[self.path]

    def __getitem__(self, attr: str) -> str:
        """Return metadata attribute."""
        return getattr(self.metadata, attr)

    def __str__(self) -> str:
        """Return string representation of the issue."""
        return textwrap.dedent(f"""
            ### Standard Name
            
            {self.name}
            
            ### Units
            
            {self["units"]}
            
            ### Documentation
            
            {self.metadata.documentation}
            
            ### Tags
            
            _No response_
            
            ### Options
            
            - [{self.overwrite}] This proposal overwrites a duplicate Standard Name.
        """).strip()


if __name__ == "__main__":
    issue = IdsIssue("pf_active", "coil/b_field_max")
    print(issue.metadata.documentation)

    print(issue["path"])
