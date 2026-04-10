"""SQLite-backed database implementations for Standard Names catalog."""

from .base import CatalogBase
from .build import CatalogBuild, build_catalog
from .integrity import verify_integrity
from .read import CatalogRead, SchemaVersionError
from .readwrite import CATALOG_SCHEMA_VERSION, DDL, CatalogReadWrite

__all__ = [
    "CATALOG_SCHEMA_VERSION",
    "CatalogBase",
    "CatalogBuild",
    "CatalogRead",
    "CatalogReadWrite",
    "DDL",
    "SchemaVersionError",
    "build_catalog",
    "verify_integrity",
]
