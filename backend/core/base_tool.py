from abc import ABC, abstractmethod
from typing import Any

from backend.core.tool_result import ToolResult


class BaseTool(ABC):
    """
    Base contract for every TCO tool.

    A tool performs a concrete, deterministic action.
    A tool should NOT make broad business decisions.
    """

    name: str = ""
    description: str = ""

    # Capabilities provided by this tool.
    # Example:
    # ("database.student.read", "database.attendance.read")
    capabilities: tuple[str, ...] = ()

    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        """
        Execute the tool.

        Every concrete tool must implement this method.
        """
        raise NotImplementedError