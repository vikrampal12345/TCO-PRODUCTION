from collections.abc import Iterable
from typing import Any

from backend.agents.assessment_agent import AssessmentAgent
from backend.agents.assessment_review_agent import AssessmentReviewAgent
from backend.core.registry import ComponentRegistry
from backend.tools.database import DatabaseTool
from backend.tools.google_forms import GoogleFormsTool
from backend.tools.gmail import GmailTool

def build_registry(
    agents: Iterable[Any] = (),
    tools: Iterable[Any] = (),
) -> ComponentRegistry:
    registry = ComponentRegistry()

    for agent in agents:
        registry.register_agent(agent)

    for tool in tools:
        registry.register_tool(tool)

    return registry


def build_default_registry() -> ComponentRegistry:
    registry = ComponentRegistry()

    # =========================
    # Agents
    # =========================

    registry.register_agent(AssessmentAgent())
    registry.register_agent(AssessmentReviewAgent())

    # Future agents:
    # registry.register_agent(EvaluationAgent())
    # registry.register_agent(AnalyticsAgent())
    # registry.register_agent(TeachingAgent())
    # registry.register_agent(AttendanceAgent())
    # registry.register_agent(CommunicationAgent())
    # registry.register_agent(ResultAgent())

    # =========================
    # Tools
    # =========================

    

    # Future tools:
    registry.register_tool(DatabaseTool())
    registry.register_tool(GoogleFormsTool())
    registry.register_tool(GmailTool())
    # registry.register_tool(ClassroomTool())
    # registry.register_tool(RAGTool())
    # registry.register_tool(WebSearchTool())

    return registry