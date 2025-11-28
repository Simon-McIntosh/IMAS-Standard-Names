# Standard Names Catalog

The Standard Names catalog is now maintained in a separate repository to allow independent versioning of catalog content.

## Catalog Repository

Visit the **[IMAS Standard Names Catalog](https://github.com/iterorganization/imas-standard-names-catalog)** repository for:

- Complete browsable catalog of all standard names
- Versioned documentation matching catalog releases
- Contribution guidelines for adding new names

## Using Standard Names

To work with standard names programmatically:

```python
from imas_standard_names.repository import StandardNameRepository

repo = StandardNameRepository()

# List all names
for name in repo.list():
    print(f"{name.name}: {name.description}")

# Get a specific name
entry = repo.get("electron_temperature")
print(f"{entry.name}: {entry.unit} - {entry.description}")
```

## CLI Tools

Use the `standard-names` CLI to search and explore:

```bash
# Search for names
standard-names search temperature

# Build catalog database
standard-names build ./standard_names --verify
```

## Documentation Resources

- **[Grammar Reference](grammar-reference.md)** - Naming rules and vocabulary
- **[Guidelines](guidelines.md)** - Best practices for standard names
- **[Contributing](development/contributing.md)** - How to propose new names
