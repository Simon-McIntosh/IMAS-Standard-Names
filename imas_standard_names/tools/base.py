"""
Base tool functionality for IMAS MCP tools.

This module contains common functionality shared across all tool implementations.
"""

import logging
from abc import ABC, abstractmethod

from imas_standard_names.repository import StandardNameCatalog

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Base class for all IMAS MCP tools with service injection."""

    def __init__(self, catalog: StandardNameCatalog | None = None):
        self.logger = logger
        if catalog is None:
            raise ValueError("BaseTool requires a catalog instance - received None")
        self.catalog = catalog

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Return the name of this tool - must be implemented by subclasses."""
        pass
