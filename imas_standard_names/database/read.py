"""Read-only on-disk SQLite catalog (snapshot consumer)."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from .base import CatalogBase
from .readwrite import CATALOG_SCHEMA_VERSION

logger = logging.getLogger(__name__)


class SchemaVersionError(Exception):
    """Raised when a catalog's schema version is incompatible."""


def _parse_version(version: str) -> tuple[int, int]:
    """Parse a 'major.minor' version string into a tuple.

    Raises:
        ValueError: If the version string is not a valid major.minor format.
    """
    try:
        parts = version.strip().split(".")
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        return major, minor
    except (ValueError, IndexError) as e:
        raise ValueError(
            f"Malformed schema version '{version}': expected 'major.minor' format"
        ) from e


class CatalogRead(CatalogBase):
    def __init__(self, db_path: Path):
        dbp = Path(db_path)
        if not dbp.exists():
            raise FileNotFoundError(f"SQLite snapshot not found: {dbp}")
        # Open in read-only mode (URI) to guard against accidental writes
        conn = sqlite3.connect(f"file:{dbp}?mode=ro", uri=True)
        super().__init__(conn)
        self._check_schema_version(dbp)

    def _check_schema_version(self, db_path: Path) -> None:
        """Validate schema version compatibility with the current reader.

        - Missing catalog_metadata table: warn (pre-versioning catalog)
        - Major version mismatch: raise SchemaVersionError
        - Minor version mismatch (db newer): warn (forward-compatible)
        """
        try:
            row = self.conn.execute(
                "SELECT value FROM catalog_metadata WHERE key = 'schema_version'"
            ).fetchone()
        except sqlite3.OperationalError:
            logger.warning(
                "Catalog %s has no catalog_metadata table "
                "(built before schema versioning was added). "
                "Rebuild with 'standard-names build' for version tracking.",
                db_path,
            )
            return

        if row is None:
            logger.warning(
                "Catalog %s has no schema_version metadata. "
                "Rebuild with 'standard-names build' for version tracking.",
                db_path,
            )
            return

        try:
            db_major, db_minor = _parse_version(row[0])
        except ValueError:
            logger.warning(
                "Catalog %s has malformed schema version '%s'. "
                "Rebuild with 'standard-names build' for version tracking.",
                db_path,
                row[0],
            )
            return

        reader_major, reader_minor = _parse_version(CATALOG_SCHEMA_VERSION)

        if db_major != reader_major:
            raise SchemaVersionError(
                f"Catalog {db_path} has schema version {row[0]} "
                f"(major={db_major}) but this version of imas-standard-names "
                f"expects schema version {CATALOG_SCHEMA_VERSION} "
                f"(major={reader_major}). "
                f"Rebuild the catalog with 'standard-names build' or update "
                f"imas-standard-names to a compatible version."
            )

        if db_minor > reader_minor:
            logger.warning(
                "Catalog %s has schema version %s (newer than reader %s). "
                "Some features may not be available. Consider updating "
                "imas-standard-names.",
                db_path,
                row[0],
                CATALOG_SCHEMA_VERSION,
            )

    # Explicitly block mutation (already guarded in base, but clearer error context)
    def insert(self, *_, **__):  # pragma: no cover
        raise RuntimeError(
            "CatalogRead is read-only; export a new snapshot to change contents"
        )

    def delete(self, *_, **__):  # pragma: no cover
        raise RuntimeError(
            "CatalogRead is read-only; export a new snapshot to change contents"
        )


__all__ = ["CatalogRead", "SchemaVersionError"]
