"""
Base tool functionality for IMAS MCP tools.

This module contains common functionality shared across all tool implementations.
"""

import logging
from abc import ABC, abstractmethod

from imas_standard_names.repository import StandardNameRepository

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Base class for all IMAS MCP tools with service injection."""

    def __init__(self, repository: StandardNameRepository | None = None):
        self.logger = logger
        self.repository = repository or StandardNameRepository()

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Return the name of this tool - must be implemented by subclasses."""
        pass
