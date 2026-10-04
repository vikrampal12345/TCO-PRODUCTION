from backend.agents.master_agent import MasterAgent
from backend.core.bootstrap import build_default_registry
from backend.core.task_executor import execute_task


# ---------------------------------------------------------
# 1. Build shared registry
# ---------------------------------------------------------

registry = build_default_registry()

print("Registry ready")


# ---------------------------------------------------------
# 2. Create Master Agent
# ---------------------------------------------------------

master = MasterAgent(
    registry=registry
)


# ---------------------------------------------------------
# 3. Teacher request
# ---------------------------------------------------------

state = {
    "teacher_request": (
        "Create a 5 question, 5 marks MCQ test "
        "on SQL using general AI knowledge."
    ),
    "request_id": "req_assessment_001",
    "teacher_id": "teacher_001",
    "conversation_id": "conv_001",
    "status": "new",
}


# ---------------------------------------------------------
# 4. Master understands and routes
# ---------------------------------------------------------

state = master.run(state)

print("\n========== MASTER DECISION ==========")

print(
    "Intent:",
    state.get("intent")
)

print(
    "Capability:",
    state.get("required_capability")
)

task = state.get("current_task")

if task is None:
    print(
        "No task created."
    )

    print(
        "Status:",
        state.get("status")
    )

    print(
        "Error:",
        state.get("error_message")
    )

    raise SystemExit(1)


print(
    "Task ID:",
    task.task_id
)

print(
    "Assigned To:",
    task.assigned_to
)

print(
    "Task Status:",
    task.status.value
)


# ---------------------------------------------------------
# 5. Execute task
# ---------------------------------------------------------

state = execute_task(
    provider=registry.get_agent(
        state["required_capability"]
    ),
    task=task,
    state=state,
)


# ---------------------------------------------------------
# 6. Show result
# ---------------------------------------------------------

print("\n========== ASSESSMENT RESULT ==========")

print(
    "Status:",
    state.get("status")
)

print(
    "Validation:",
    state.get("validation_status")
)

print(
    "Message:",
    state.get("assessment_message")
)


questions = state.get(
    "questions",
    []
)

print(
    "\nQuestions generated:",
    len(questions)
)


for question in questions:

    print(
        f"\nQ{question['question_number']}: "
        f"{question['question']}"
    )

    for index, option in enumerate(
        question["options"],
        start=1,
    ):
        print(
            f"  {index}. {option}"
        )

    print(
        "Correct option:",
        question["correct_option"]
    )

    print(
        "Marks:",
        question["marks"]
    )


print("\n========== E2E ASSESSMENT TEST PASSED ==========")