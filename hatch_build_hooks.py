"""Custom Hatch build hook that regenerates grammar types before builds.

Configured via:

    [tool.hatch.build.hooks.custom]
    path = "hatch_build_hooks.py"

This executes within the Hatch build environment.
"""

from __future__ import annotations

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    """Run the grammar generator so types.py is up to date."""

    def initialize(self, version: str, build_data: dict) -> None:  # noqa: D401
        # Ensure the project source root is importable while building
        import sys  # noqa: PLC0415

        if self.root not in sys.path:
            sys.path.insert(0, self.root)

        # Execute the generator module by path to avoid importing
        # the grammar package (which would expect types.py to exist).
        import os  # noqa: PLC0415
        import runpy  # noqa: PLC0415

        gen_path = os.path.join(
            self.root,
            "imas_standard_names",
            "grammar_codegen",
            "generate.py",
        )
        ctx = runpy.run_path(gen_path)
        ctx["main"]()
