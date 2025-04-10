from dataclasses import dataclass
from functools import cached_property

import imas


@dataclass
class IdsIssue:
    name: str
    path: str

    @cached_property
    def metadata(self):
        """Return metadata for IDS attribute at path."""
        return imas.IDSFactory().new(self.name).metadata[self.path]

    def __getitem__(self, attr: str) -> str:
        """Return metadata attribute."""
        return getattr(self.metadata, attr)


if __name__ == "__main__":
    issue = IdsIssue("pf_active", "coil/b_field_max")
    print(issue.metadata.documentation)

    print(issue["path"])
