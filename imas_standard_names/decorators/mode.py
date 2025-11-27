"""Write mode guards for catalog operations.

Provides decorators to enforce write access requirements at runtime.
"""

from __future__ import annotations

import asyncio
import functools
from typing import Callable, TypeVar

__all__ = ["requires_write_mode", "ReadOnlyModeError"]

T = TypeVar("T")


class ReadOnlyModeError(Exception):
    """Raised when write operation attempted on read-only catalog."""
    
    def __init__(self, operation: str, catalog_info: str | None = None):
        catalog_details = f"\nCurrent catalog: {catalog_info}" if catalog_info else ""
        msg = (
            f"Operation '{operation}' requires writable catalog.{catalog_details}\n\n"
            f"To enable editing:\n"
            f"  1. Clone catalog: git clone https://github.com/iterorg/imas-standard-names-catalog.git\n"
            f"  2. Set path: export STANDARD_NAMES_CATALOG_ROOT=./imas-standard-names-catalog/standard_names\n"
            f"  3. Restart server\n\n"
            f"Or download and use local catalog:\n"
            f"  1. Download from: https://github.com/iterorg/imas-standard-names-catalog/releases\n"
            f"  2. Extract and set: export STANDARD_NAMES_CATALOG_ROOT=/path/to/standard_names\n\n"
            f"Install quality tools for full capabilities:\n"
            f"  pip install imas-standard-names[quality]"
        )
        super().__init__(msg)


def requires_write_mode(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to guard write operations based on runtime catalog state.
    
    Checks if the catalog is writable before allowing the operation.
    Works with both sync and async functions.
    """
    
    @functools.wraps(func)
    def sync_wrapper(self, *args, **kwargs):
        # Check if catalog is writable
        if hasattr(self, 'catalog') and hasattr(self.catalog, 'read_only'):
            if self.catalog.read_only:
                catalog_info = None
                if hasattr(self.catalog, 'paths') and self.catalog.paths:
                    catalog_info = str(self.catalog.paths.yaml_path)
                elif hasattr(self.catalog, 'catalog_path'):
                    catalog_info = str(self.catalog.catalog_path)
                else:
                    catalog_info = "bundled catalog"
                raise ReadOnlyModeError(func.__name__, catalog_info)
        return func(self, *args, **kwargs)
    
    @functools.wraps(func)
    async def async_wrapper(self, *args, **kwargs):
        # Check if catalog is writable
        if hasattr(self, 'catalog') and hasattr(self.catalog, 'read_only'):
            if self.catalog.read_only:
                catalog_info = None
                if hasattr(self.catalog, 'paths') and self.catalog.paths:
                    catalog_info = str(self.catalog.paths.yaml_path)
                elif hasattr(self.catalog, 'catalog_path'):
                    catalog_info = str(self.catalog.catalog_path)
                else:
                    catalog_info = "bundled catalog"
                raise ReadOnlyModeError(func.__name__, catalog_info)
        return await func(self, *args, **kwargs)
    
    # Return appropriate wrapper based on function type
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper
