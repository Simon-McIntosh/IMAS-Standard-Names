"""Catalog package.

Exposes the SPA dataset builder used to convert the published YAML
catalog into the JSON shape consumed by the redesigned SPA, and the
versioned ``gh-pages`` deployer used by ``standard-names site-deploy``
to publish the built SPA.
"""

from .dataset import build_site_dataset, write_site_dataset
from .gh_pages import VersionEntry, deploy

__all__ = [
    "VersionEntry",
    "build_site_dataset",
    "deploy",
    "write_site_dataset",
]
