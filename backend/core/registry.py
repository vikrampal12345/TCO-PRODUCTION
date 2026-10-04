from typing import Any


class RegistryError(Exception):
    """Base exception for registry-related errors."""


class CapabilityAlreadyRegisteredError(RegistryError):
    """Raised when a capability is already registered."""


class CapabilityNotFoundError(RegistryError):
    """Raised when a capability has no registered provider."""


class ComponentRegistry:
    """
    Central registry for TCO agents and tools.

    The registry maps capabilities to components that provide them.

    Example:
        assessment.create -> AssessmentAgent
        attendance.read  -> DatabaseTool
    """

    def __init__(self) -> None:
        self._agents: dict[str, Any] = {}
        self._tools: dict[str, Any] = {}

        self._agent_capabilities: dict[str, str] = {}
        self._tool_capabilities: dict[str, str] = {}

    # ---------------------------------------------------------
    # AGENTS
    # ---------------------------------------------------------

    def register_agent(self, agent: Any) -> None:
        """Register an agent and all its capabilities."""

        name = getattr(agent, "name", "").strip()
        capabilities = getattr(agent, "capabilities", ())

        if not name:
            raise RegistryError("Agent must have a name.")

        if name in self._agents:
            raise RegistryError(
                f"Agent '{name}' is already registered."
            )

        self._validate_capabilities(
            capabilities,
            "agent",
            name,
        )

        self._agents[name] = agent

        for capability in capabilities:
            self._agent_capabilities[capability] = name

    def get_agent(self, capability: str) -> Any:
        """Return the agent responsible for a capability."""

        agent_name = self._agent_capabilities.get(capability)

        if not agent_name:
            raise CapabilityNotFoundError(
                f"No agent registered for capability "
                f"'{capability}'."
            )

        return self._agents[agent_name]

    # ---------------------------------------------------------
    # TOOLS
    # ---------------------------------------------------------

    def register_tool(self, tool: Any) -> None:
        """Register a tool and all its capabilities."""

        name = getattr(tool, "name", "").strip()
        capabilities = getattr(tool, "capabilities", ())

        if not name:
            raise RegistryError("Tool must have a name.")

        if name in self._tools:
            raise RegistryError(
                f"Tool '{name}' is already registered."
            )

        self._validate_capabilities(
            capabilities,
            "tool",
            name,
        )

        self._tools[name] = tool

        for capability in capabilities:
            self._tool_capabilities[capability] = name

    def get_tool(self, capability: str) -> Any:
        """Return the tool responsible for a capability."""

        tool_name = self._tool_capabilities.get(capability)

        if not tool_name:
            raise CapabilityNotFoundError(
                f"No tool registered for capability "
                f"'{capability}'."
            )

        return self._tools[tool_name]

    # ---------------------------------------------------------
    # LOOKUP
    # ---------------------------------------------------------

    def has_agent(self, capability: str) -> bool:
        """Check whether an agent provides a capability."""

        return capability in self._agent_capabilities

    def has_tool(self, capability: str) -> bool:
        """Check whether a tool provides a capability."""

        return capability in self._tool_capabilities

    def has_capability(self, capability: str) -> bool:
        """Check whether any registered component provides a capability."""

        return (
            capability in self._agent_capabilities
            or capability in self._tool_capabilities
        )

    # ---------------------------------------------------------
    # CAPABILITY CATALOG
    # ---------------------------------------------------------

    def get_capability_catalog(self) -> dict[str, list[dict[str, str]]]:
        """
        Return the capabilities currently available to the system.

        This allows the Master Agent to make routing decisions
        dynamically instead of maintaining hard-coded if/else rules.
        """

        agents = []

        for capability, agent_name in sorted(
            self._agent_capabilities.items()
        ):
            agent = self._agents[agent_name]

            agents.append(
                {
                    "capability": capability,
                    "provider": agent_name,
                    "type": "agent",
                    "description": getattr(
                        agent,
                        "description",
                        "",
                    ),
                }
            )

        tools = []

        for capability, tool_name in sorted(
            self._tool_capabilities.items()
        ):
            tool = self._tools[tool_name]

            tools.append(
                {
                    "capability": capability,
                    "provider": tool_name,
                    "type": "tool",
                    "description": getattr(
                        tool,
                        "description",
                        "",
                    ),
                }
            )

        return {
            "agents": agents,
            "tools": tools,
        }

    # ---------------------------------------------------------
    # VALIDATION
    # ---------------------------------------------------------

    def _validate_capabilities(
        self,
        capabilities: tuple[str, ...],
        component_type: str,
        component_name: str,
    ) -> None:
        """Validate capability names and prevent duplicates."""

        for capability in capabilities:

            if not isinstance(capability, str):
                raise RegistryError(
                    f"Capability must be a string in "
                    f"{component_type} '{component_name}'."
                )

            capability = capability.strip()

            if not capability:
                raise RegistryError(
                    f"Empty capability found in "
                    f"{component_type} '{component_name}'."
                )

            already_agent = capability in self._agent_capabilities
            already_tool = capability in self._tool_capabilities

            if already_agent:
                raise CapabilityAlreadyRegisteredError(
                    f"Capability '{capability}' is already "
                    f"registered by agent "
                    f"'{self._agent_capabilities[capability]}'."
                )

            if already_tool:
                raise CapabilityAlreadyRegisteredError(
                    f"Capability '{capability}' is already "
                    f"registered by tool "
                    f"'{self._tool_capabilities[capability]}'."
                )