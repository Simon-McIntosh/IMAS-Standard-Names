"""Scalar Standard Name example.

Demonstrates:
  * Creating an isolated writable repo root under a temporary directory
  * Adding several valid scalar standard names within a UnitOfWork
    * Handling duplicate name and invalid pattern anti‑patterns
    * Single-step undo of most recent change via UnitOfWork.undo_last()
  * Committing to persist YAML, then inspecting persisted files
  * Automatic cleanup (temp directory removed on exit)

Run:
    python examples/add_scalar.py

"""

from __future__ import annotations

import tempfile
from contextlib import contextmanager
from pathlib import Path
from pprint import pprint

from imas_standard_names.repository import StandardNameRepository
from imas_standard_names.schema import create_standard_name


# ---------------------------------------------------------------------------
# Context manager to create and cleanup a temporary repository root
# ---------------------------------------------------------------------------
@contextmanager
def temporary_repo_root():
    with tempfile.TemporaryDirectory(prefix="stdnames_") as tmp:
        root = Path(tmp) / "standard_names"
        root.mkdir(parents=True, exist_ok=True)
        yield root  # directory removed automatically afterwards


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def make_scalar(name: str, unit: str, description: str, status: str = "draft"):
    return create_standard_name(
        {
            "name": name,
            "kind": "scalar",
            "unit": unit,
            "description": description,
            "status": status,
        }
    )


def demo():
    with temporary_repo_root() as root:
        print(f"Temporary repo root: {root}")
        repo = StandardNameRepository(root)
        print("Initial count:", len(repo))

        uow = repo.start_uow()

        # Valid scalars ------------------------------------------------------
        scalars = [
            ("ion_density", "m^-3", "Ion number density."),
            ("electron_temperature", "eV", "Electron temperature."),
            ("ion_temperature", "eV", "Ion temperature."),
        ]

        for name, unit, desc in scalars:
            uow.add(make_scalar(name, unit, desc))
            print(f"Staged: {name}")

        print("Count after staging valid entries:", len(repo))

        # Undo last demonstration -----------------------------------------
        print("\n-- Undo last demo --")
        temp1 = make_scalar("temp_scalar_one", "eV", "Temporary A")
        temp2 = make_scalar("temp_scalar_two", "eV", "Temporary B")
        uow.add(temp1)
        uow.add(temp2)
        print(
            "Added temp scalars. Contains temp_scalar_one?",
            repo.exists("temp_scalar_one"),
        )
        print(
            "Added temp scalars. Contains temp_scalar_two?",
            repo.exists("temp_scalar_two"),
        )
        uow.undo_last()  # removes temp_scalar_two only
        print(
            "After undo_last -> temp_scalar_one exists?",
            repo.exists("temp_scalar_one"),
        )
        print(
            "After undo_last -> temp_scalar_two exists?",
            repo.exists("temp_scalar_two"),
        )

        # Rollback demonstration (full revert) -----------------------------
        print("\n-- Rollback demo --")
        transient = make_scalar("transient_probe_scalar", "m.s", "Will be rolled back")
        uow.add(transient)
        print("Added transient entry. Count now:", len(repo))
        print("Rolling back transient change (before other demos)...")
        uow.rollback()
        print("Baseline scalars after rollback (catalog reset). Count:", len(repo))

        # Start a fresh UnitOfWork after rollback to continue normal flow
        uow = repo.start_uow()
        # Re-stage original valid scalars (replicating earlier state)
        for name, unit, desc in scalars:
            uow.add(make_scalar(name, unit, desc))
        print("Re-staged baseline scalars after rollback. Count:", len(repo))

        # Anti‑patterns / errors --------------------------------------------
        print("\n-- Anti‑patterns --")
        try:
            # Duplicate add (already staged)
            uow.add(make_scalar("ion_density", "m^-3", "Duplicate ion density."))
        except ValueError as e:
            print("Duplicate name error caught:", e)

        try:
            # Naming anti-pattern: time derivative suffix instead of prefix form
            uow.add(
                make_scalar(
                    "electron_temperature_time_derivative",
                    "eV.s^-1",
                    "Bad derivative naming.",
                )
            )
        except ValueError as e:
            print("Schema validation error (example):", e)
        except Exception as e:  # broad catch to illustrate handling
            print("Caught generic error for anti-pattern name:", e)

        # Show staged entries (includes ones that succeeded)
        staged_names = repo.list_names()
        print("\nStaged names:")
        pprint(staged_names)

        print("Validating before commit...")
        issues = uow.validate()
        if issues:
            print("Validation issues:")
            for i in issues:
                print(" -", i)
            print("Rolling back due to issues.")
            uow.rollback()
            return

        print("No validation issues. Committing...")
        uow.commit()

        print("\nCommit complete. YAML files:")
        for yml in sorted(root.rglob("*.yml")):
            print(" -", yml.relative_to(root.parent))

        # Fresh load to prove persistence
        repo2 = StandardNameRepository(root)
        print("Reloaded count:", len(repo2))
        print("Exists ion_density?", repo2.exists("ion_density"))

        # Sample retrieval
        model = repo2.get("ion_density")
        print("Ion density status:", model.status if model else None)


if __name__ == "__main__":  # pragma: no cover
    demo()
