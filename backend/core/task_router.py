from backend.core.registry import (
    ComponentRegistry,
    CapabilityNotFoundError,
)
from backend.core.task import Task


class TaskRouter:
    """
    Routes a Task to the registered agent or tool
    that provides the required capability.

    The router does NOT decide what the teacher wants.
    The Master Agent is responsible for that decision.
    """

    def __init__(self, registry: ComponentRegistry):
        self.registry = registry

    def route(self, task: Task):
        """
        Find the correct provider for the task
        and assign the task to it.

        Returns:
            (provider, task)
        """

        capability = task.capability

        # Prefer a specialist agent when one provides
        # the requested capability.
        if self.registry.has_agent(capability):
            agent = self.registry.get_agent(capability)

            task.start(agent.name)

            return agent, task

        # Otherwise route to a deterministic tool.
        if self.registry.has_tool(capability):
            tool = self.registry.get_tool(capability)

            task.start(tool.name)

            return tool, task

        raise CapabilityNotFoundError(
            f"No agent or tool found for capability "
            f"'{capability}'."
        )