from backend.agents.master_agent import MasterAgent
from backend.core.base_agent import BaseAgent
from backend.core.base_tool import BaseTool
from backend.core.registry import ComponentRegistry
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
    description = "Reads student and attendance records."
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
# Registry
# ---------------------------------------------------------

registry = ComponentRegistry()

registry.register_agent(
    DummyAssessmentAgent()
)

registry.register_tool(
    DummyDatabaseTool()
)


# ---------------------------------------------------------
# Master
# ---------------------------------------------------------

master = MasterAgent(
    registry=registry
)


# ---------------------------------------------------------
# TEST 1
# Assessment request
# ---------------------------------------------------------

assessment_state = {
    "teacher_request": (
        "Class 10 Science ke Light chapter ka "
        "5 questions aur 20 marks ka test banao."
    ),
    "request_id": "req_001",
    "teacher_id": "teacher_001",
    "status": "new",
}

result = master.run(assessment_state)

print("\n========== TEST 1 ==========")
print("Intent:", result.get("intent"))
print(
    "Capability:",
    result.get("required_capability")
)

task = result.get("current_task")

if task:
    print("Task ID:", task.task_id)
    print("Assigned To:", task.assigned_to)
    print("Task Status:", task.status.value)

print("Overall Status:", result.get("status"))


# ---------------------------------------------------------
# TEST 2
# Attendance request
# ---------------------------------------------------------

attendance_state = {
    "teacher_request": (
        "Rahul ka attendance check karo."
    ),
    "request_id": "req_002",
    "teacher_id": "teacher_001",
    "status": "new",
}

result = master.run(attendance_state)

print("\n========== TEST 2 ==========")
print("Intent:", result.get("intent"))
print(
    "Capability:",
    result.get("required_capability")
)

task = result.get("current_task")

if task:
    print("Task ID:", task.task_id)
    print("Assigned To:", task.assigned_to)
    print("Task Status:", task.status.value)

print("Overall Status:", result.get("status"))


print("\nMASTER ROUTING TEST COMPLETED")