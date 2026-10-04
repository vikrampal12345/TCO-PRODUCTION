from backend.core.base_agent import BaseAgent
from backend.core.base_tool import BaseTool
from backend.core.bootstrap import build_registry
from backend.core.tool_result import ToolResult


class DummyAssessmentAgent(BaseAgent):

    name = "assessment_agent"
    description = "Creates assessments."

    capabilities = (
        "assessment.create",
    )

    def run(self, state, task=None):
        return state


class DummyDatabaseTool(BaseTool):

    name = "database"
    description = "Reads student records."

    capabilities = (
        "attendance.read",
    )

    def execute(self, **kwargs):
        return ToolResult.ok(
            {
                "student": kwargs.get("student"),
                "attendance": 85,
            }
        )


# ---------------------------------------------------------
# Build shared registry
# ---------------------------------------------------------

registry = build_registry(
    agents=[
        DummyAssessmentAgent(),
    ],
    tools=[
        DummyDatabaseTool(),
    ],
)


# ---------------------------------------------------------
# Verify registrations
# ---------------------------------------------------------

assert registry.has_agent(
    "assessment.create"
)

assert registry.has_tool(
    "attendance.read"
)


# ---------------------------------------------------------
# Verify provider lookup
# ---------------------------------------------------------

assessment_agent = registry.get_agent(
    "assessment.create"
)

database_tool = registry.get_tool(
    "attendance.read"
)


print(
    "Assessment provider:",
    assessment_agent.name
)

print(
    "Attendance provider:",
    database_tool.name
)

print("\nBOOTSTRAP TEST PASSED")