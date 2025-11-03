"""Base tool functionality for IMAS MCP tools.

This module contains common functionality shared across all tool implementations.
"""

import logging
from abc import ABC, abstractmethod

from imas_standard_names.repository import StandardNameCatalog

logger = logging.getLogger(__name__)


class Tool(ABC):
    """Minimal base class for all IMAS MCP tools."""

    def __init__(self):
        self.logger = logger

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Return the name of this tool - must be implemented by subclasses."""
        pass


class CatalogTool(Tool):
    """Base class for tools that operate on catalog data."""

    def __init__(self, catalog: StandardNameCatalog | None = None):
        super().__init__()
        if catalog is None:
            raise ValueError("CatalogTool requires a catalog instance - received None")
        self.catalog = catalog
