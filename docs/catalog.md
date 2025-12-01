# Standard Names Catalog

The Standard Names catalog is maintained in a separate repository to allow independent versioning of catalog content.

## Catalog Repository

Visit the **[IMAS Standard Names Catalog](https://github.com/iterorganization/imas-standard-names-catalog)** repository for:

- Complete browsable catalog of all standard names
- Versioned documentation matching catalog releases
- Contribution guidelines for adding new names

## Installation

```bash
# Install catalog package (recommended)
pip install imas-standard-names-catalog

# Or download pre-built database
wget https://github.com/iterorganization/imas-standard-names-catalog/releases/latest/download/catalog.db
export STANDARD_NAMES_CATALOG_DB=./catalog.db
```

## Using Standard Names

```python
from imas_standard_names import StandardNameCatalog

catalog = StandardNameCatalog()

# List all names
for entry in catalog.list():
    print(f"{entry.name}: {entry.description}")

# Get a specific name
entry = catalog.get("electron_temperature")
print(f"{entry.name}: {entry.unit} - {entry.description}")
```

## Documentation Resources

- **[Grammar Reference](grammar-reference.md)** - Naming rules and vocabulary
- **[Guidelines](guidelines.md)** - Best practices for standard names
- **[Contributing](development/contributing.md)** - How to propose new names
