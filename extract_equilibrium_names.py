#!/usr/bin/env python3
"""Extract all equilibrium-tagged standard names to CSV."""

import csv
from pathlib import Path

from imas_standard_names.repository import StandardNameCatalog


def main():
    """Extract equilibrium standard names and write to CSV."""
    # Initialize catalog from packaged resources
    catalog = StandardNameCatalog()
    
    # Get all equilibrium-tagged standard names
    equilibrium_names = catalog.list(tags="equilibrium")
    
    print(f"Found {len(equilibrium_names)} equilibrium-tagged standard names")
    
    # Output path
    output_path = Path(__file__).parent / "resources" / "equilibrium_standard_names.csv"
    
    # Write to CSV
    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["name", "kind", "unit", "status", "description", "tags"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for entry in equilibrium_names:
            writer.writerow({
                "name": entry.name,
                "kind": entry.kind,
                "unit": entry.unit,
                "status": entry.status,
                "description": entry.description,
                "tags": ", ".join(entry.tags),
            })
    
    print(f"Wrote {len(equilibrium_names)} entries to {output_path}")


if __name__ == "__main__":
    main()
