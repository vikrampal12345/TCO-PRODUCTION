from collections.abc import Iterable
from typing import Any

from backend.agents.assessment_agent import AssessmentAgent
from backend.agents.assessment_review_agent import AssessmentReviewAgent

from backend.core.registry import ComponentRegistry

from backend.tools.database import DatabaseTool
from backend.tools.google_forms import GoogleFormsTool
from backend.tools.google_forms_identity import GoogleFormsIdentityTool
from backend.tools.gmail import GmailTool


def build_registry(
    agents: Iterable[Any] = (),
    tools: Iterable[Any] = (),
) -> ComponentRegistry:
    """
    Build a ComponentRegistry from the supplied agents and tools.
    """

    registry = ComponentRegistry()

    # =========================================================
    # REGISTER AGENTS
    # =========================================================

    for agent in agents:
        registry.register_agent(agent)

    # =========================================================
    # REGISTER TOOLS
    # =========================================================

    for tool in tools:
        registry.register_tool(tool)

    return registry


def build_default_registry() -> ComponentRegistry:
    """
    Build the default TCO component registry.

    This registry is the central dependency container used by
    the Master Agent and workflows.

    Registered agents:
        - Assessment Agent
        - Assessment Review Agent

    Registered tools:
        - Database Tool
        - Google Forms Tool
        - Google Forms Identity Tool
        - Gmail Tool
    """

    registry = ComponentRegistry()

    # =========================================================
    # AGENTS
    # =========================================================

    registry.register_agent(
        AssessmentAgent()
    )

    registry.register_agent(
        AssessmentReviewAgent()
    )

    # Future specialist agents:
    #
    # registry.register_agent(
    #     EvaluationAgent()
    # )
    #
    # registry.register_agent(
    #     AnalyticsAgent()
    # )
    #
    # registry.register_agent(
    #     TeachingAgent()
    # )
    #
    # registry.register_agent(
    #     AttendanceAgent()
    # )
    #
    # registry.register_agent(
    #     CommunicationAgent()
    # )
    #
    # registry.register_agent(
    #     ResultAgent()
    # )

    # =========================================================
    # TOOLS
    # =========================================================

    registry.register_tool(
        DatabaseTool()
    )

    registry.register_tool(
        GoogleFormsTool()
    )

    # ---------------------------------------------------------
    # Student identity field tool
    #
    # Capability:
    #     form.identity.add
    #
    # This tool adds:
    #     Student ID / Roll Number
    #
    # to every TCO Google Form.
    # ---------------------------------------------------------

    registry.register_tool(
        GoogleFormsIdentityTool()
    )

    registry.register_tool(
        GmailTool()
    )

    # Future tools:
    #
    # registry.register_tool(
    #     ClassroomTool()
    # )
    #
    # registry.register_tool(
    #     RAGTool()
    # )
    #
    # registry.register_tool(
    #     WebSearchTool()
    # )

    return registry