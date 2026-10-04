from backend.core.base_agent import BaseAgent
from backend.core.base_tool import BaseTool
from backend.core.registry import ComponentRegistry
from backend.core.task import Task
from backend.core.task_router import TaskRouter
from backend.core.tool_result import ToolResult


class DummyAssessmentAgent(BaseAgent):
    name = "assessment_agent"

    capabilities = (
        "assessment.create",
    )

    def run(self, state, task=None):
        return state


class DummyDatabaseTool(BaseTool):
    name = "database"

    description = "Dummy database tool for testing."

    capabilities = (
        "attendance.read",
    )

    def execute(self, **kwargs):
        return ToolResult.ok(
            data={"student": "Rahul", "attendance": 85}
        )


# ---------------------------------------------------------
# Registry
# ---------------------------------------------------------

registry = ComponentRegistry()

assessment_agent = DummyAssessmentAgent()
database_tool = DummyDatabaseTool()

registry.register_agent(assessment_agent)
registry.register_tool(database_tool)


# ---------------------------------------------------------
# Router
# ---------------------------------------------------------

router = TaskRouter(registry)


# ---------------------------------------------------------
# Test 1: Agent routing
# ---------------------------------------------------------

assessment_task = Task(
    capability="assessment.create",
    input_data={
        "class_level": "10",
        "subject": "Science",
        "marks": 20,
    },
)

provider, assessment_task = router.route(assessment_task)

print("TEST 1")
print("Provider:", provider.name)
print("Status:", assessment_task.status.value)
print()


# ---------------------------------------------------------
# Test 2: Tool routing
# ---------------------------------------------------------

attendance_task = Task(
    capability="attendance.read",
    input_data={
        "student": "Rahul",
    },
)

provider, attendance_task = router.route(attendance_task)

print("TEST 2")
print("Provider:", provider.name)
print("Status:", attendance_task.status.value)
print()


# ---------------------------------------------------------
# Final
# ---------------------------------------------------------

print("ROUTING TEST PASSED")