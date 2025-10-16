"""Shared pytest fixtures for IMAS Standard Names tests."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from imas_standard_names.catalog.edit import EditCatalog
from imas_standard_names.repository import StandardNameCatalog
from imas_standard_names.tools.create import CreateTool
from imas_standard_names.tools.fetch import FetchTool
from imas_standard_names.tools.write import WriteTool
from imas_standard_names.yaml_store import YamlStore


# Configure pytest-anyio to only use asyncio backend (trio not installed)
# This prevents pytest from parameterizing tests with trio backend
@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
def temp_catalog_dir(tmp_path):
    """Create a temporary directory for catalog YAML files."""
    catalog_dir = tmp_path / "catalog"
    catalog_dir.mkdir()
    return catalog_dir


@pytest.fixture
def temp_catalog(temp_catalog_dir):
    """Create a StandardNameCatalog using temporary storage.

    This catalog starts empty and is isolated from the production catalog.
    All changes are scoped to the test and cleaned up automatically.
    """
    catalog = StandardNameCatalog(root=temp_catalog_dir)
    return catalog


@pytest.fixture
def temp_edit_catalog(temp_catalog):
    """Create an EditCatalog wrapping the temporary catalog."""
    return EditCatalog(temp_catalog)


@pytest.fixture
def temp_create_tool(temp_catalog, temp_edit_catalog):
    """Create a CreateTool using the temporary catalog."""
    return CreateTool(temp_catalog, temp_edit_catalog)


@pytest.fixture
def temp_write_tool(temp_catalog, temp_edit_catalog):
    """Create a WriteTool using the temporary catalog."""
    return WriteTool(temp_catalog, temp_edit_catalog)


@pytest.fixture
def temp_fetch_tool(temp_catalog):
    """Create a FetchTool using the temporary catalog."""
    return FetchTool(temp_catalog)


@pytest.fixture
def invoke_async():
    """Helper to invoke async tool methods synchronously."""

    def _invoke(tool, method_name, **kwargs):
        method = getattr(tool, method_name)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(method(**kwargs))

    return _invoke


@pytest.fixture
def sample_scalar_entry():
    """Sample scalar catalog entry for testing."""
    return {
        "name": "test_scalar",
        "kind": "scalar",
        "description": "Test scalar entry.",
        "unit": "m",
        "status": "draft",
        "tags": ["magnetics", "measured"],
    }


@pytest.fixture
def sample_vector_entry():
    """Sample vector catalog entry for testing."""
    return {
        "name": "test_vector",
        "kind": "vector",
        "description": "Test vector entry.",
        "unit": "T",
        "status": "draft",
        "tags": ["magnetics", "spatial-profile"],
    }


@pytest.fixture
def sample_entries_with_provenance():
    """Sample entries with various provenance patterns."""
    return [
        {
            "name": "base_quantity",
            "kind": "scalar",
            "description": "Base quantity for provenance tests.",
            "unit": "m",
            "tags": ["magnetics"],
        },
        {
            "name": "derived_quantity",
            "kind": "scalar",
            "description": "Derived quantity using operator.",
            "unit": "m.s^-1",
            "tags": ["magnetics", "derived"],
            "provenance": {
                "mode": "operator",
                "operators": ["time_derivative"],
                "base": "base_quantity",
                "operator_id": "time_derivative",
            },
        },
    ]


@pytest.fixture
def sample_catalog(tmp_path):
    """Create a StandardNameCatalog pre-populated with sample entries.

    This fixture provides a catalog with several standard entries for tests
    that need existing data (e.g., testing search, list, edit operations).
    Includes scalars and vectors for comprehensive testing.
    Isolated from production catalog and cleaned up automatically.
    """
    catalog_dir = tmp_path / "sample_catalog"
    catalog_dir.mkdir()

    # Create subdirectories for primary tags
    (catalog_dir / "fundamental").mkdir()
    (catalog_dir / "magnetics").mkdir()
    (catalog_dir / "equilibrium").mkdir()
    (catalog_dir / "core-physics").mkdir()
    (catalog_dir / "transport").mkdir()

    # Sample entries - mix of scalars and vectors with valid tags
    sample_entries = {
        # Scalar entries
        "fundamental/magnetic_field.yml": """name: magnetic_field
kind: scalar
description: Magnitude of the magnetic field vector
unit: T
tags:
  - fundamental
  - measured
status: active
""",
        "fundamental/electron_density.yml": """name: electron_density
kind: scalar
description: Electron number density
unit: m^-3
tags:
  - fundamental
  - measured
status: active
""",
        "magnetics/poloidal_magnetic_field.yml": """name: poloidal_magnetic_field
kind: scalar
description: Poloidal component of magnetic field
unit: T
tags:
  - magnetics
  - measured
status: active
""",
        "equilibrium/plasma_current.yml": """name: plasma_current
kind: scalar
description: Total plasma current
unit: A
tags:
  - equilibrium
  - measured
status: active
""",
        "fundamental/ion_temperature.yml": """name: ion_temperature
kind: scalar
description: Ion temperature
unit: eV
tags:
  - fundamental
  - measured
status: active
""",
        "fundamental/electron_temperature.yml": """name: electron_temperature
kind: scalar
description: Electron temperature
unit: eV
tags:
  - fundamental
  - measured
status: active
""",
        # Vector entries (use primary tags: core-physics, edge-physics, magnetics)
        "core-physics/electron_density_profile.yml": """name: electron_density_profile
kind: vector
description: Radial profile of electron number density
unit: m^-3
tags:
  - core-physics
  - spatial-profile
  - measured
status: active
""",
        "core-physics/electron_temperature_profile.yml": """name: electron_temperature_profile
kind: vector
description: Radial profile of electron temperature
unit: eV
tags:
  - core-physics
  - spatial-profile
  - measured
status: active
""",
        "magnetics/magnetic_field_components.yml": """name: magnetic_field_components
kind: vector
description: Components of the magnetic field vector
unit: T
tags:
  - magnetics
  - measured
status: active
""",
        "core-physics/ion_temperature_profile.yml": """name: ion_temperature_profile
kind: vector
description: Radial profile of ion temperature
unit: eV
tags:
  - core-physics
  - spatial-profile
  - measured
status: active
""",
        # Entry with operator provenance (gradient)
        "transport/electron_density_gradient.yml": """name: electron_density_gradient
kind: vector
description: Gradient of electron density
unit: m^-3.m^-1
tags:
  - transport
  - derived
  - spatial-profile
status: active
provenance:
  mode: operator
  operators:
    - gradient
  operator_id: gradient
  base: electron_density
""",
    }  # Write sample entries to disk
    for rel_path, content in sample_entries.items():
        file_path = catalog_dir / rel_path
        file_path.write_text(content)

    # Return initialized catalog
    return StandardNameCatalog(root=catalog_dir)
