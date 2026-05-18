"""Catalog package.

Currently exposes the SPA dataset builder used to convert the published
YAML catalog into the JSON shape consumed by the redesigned SPA.
"""

from .dataset import build_site_dataset, write_site_dataset

__all__ = [
    "build_site_dataset",
    "write_site_dataset",
]
