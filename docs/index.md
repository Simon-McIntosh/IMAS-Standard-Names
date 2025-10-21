# IMAS Standard Names

Welcome to the IMAS Standard Names catalog  a comprehensive collection of structured, machine-parseable names for fusion data variables.

{% set stats = category_stats() %}

## Standard Name Categories

Browse standard names by category:

{% for tag, items in stats.tags.items() %}
- **[{{ tag.replace('-', ' ').title() }}](catalog.md#{{ tag }})**  {{ items|length }} standard names
{% endfor %}

## Statistics

- **Total Standard Names:** {{ stats.total_names }}
- **Categories:** {{ stats.total_tags }}

---

## About Standard Names

Standard names provide a controlled vocabulary for identifying physical quantities, diagnostic measurements, and geometric properties in fusion experiments. Each name includes:

- **Unique identifier** following grammar rules
- **Physical units** (SI-consistent)
- **Description** and detailed documentation
- **Category tags** for organization
- **Status** tracking (draft, active, deprecated)

## Documentation

- **[Standard Names Catalog](catalog.md)**  Complete browsable catalog
- **[Grammar Reference](grammar-reference.md)**  Vocabulary and naming rules
- **[Guidelines](guidelines.md)**  Naming patterns and conventions
- **[Development Guides](development/quickstart.md)**  For contributors

## Programmatic Access

```python
from imas_standard_names.repository import StandardNameRepository

repo = StandardNameRepository()
name = repo.get(\"electron_temperature\")
print(f\"{name.name}: {name.unit}  {name.description}\")
```
