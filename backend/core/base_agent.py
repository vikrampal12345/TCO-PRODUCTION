from abc import ABC, abstractmethod
from typing import Any

from backend.state import TCOState


class BaseAgent(ABC):
    """
    Common contract for every specialist agent in TCO.

    Every agent must:
    - have a unique name
    - declare the capabilities it provides
    - implement the run() method
    """

    name: str = ""
    capabilities: tuple[str, ...] = ()

    @abstractmethod
    def run(
        self,
        state: TCOState,
        task: dict[str, Any] | None = None,
    ) -> TCOState:
        """
        Execute an assigned task.

        Parameters:
            state: Shared TCO execution state.
            task: Task assigned by the Master/Task system.

        Returns:
            Updated TCOState.
        """
        raise NotImplementedError