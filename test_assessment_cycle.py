from backend.core.bootstrap import build_default_registry
from backend.services.assessment_cycle import run_assessment_cycle


# ---------------------------------------------------------
# Build shared registry
# ---------------------------------------------------------

registry = build_default_registry()

print("Registry ready")


# ---------------------------------------------------------
# Teacher request already understood by Master
# ---------------------------------------------------------

state = {
    "teacher_request": (
        "Create a 5 question, 5 marks MCQ test "
        "on SQL using general AI knowledge."
    ),

    "request_id": "req_cycle_001",
    "teacher_id": "teacher_001",
    "conversation_id": "conv_001",

    "intent": "assessment",

    "required_capability": "assessment.create",

    "topic": "SQL",
    "subject": "Database Management",
    "class_level": "10",

    "question_count": 5,
    "marks": 5,

    "generation_mode": "llm_generated",

    "assessment_review_attempts": 0,
    "assessment_max_review_attempts": 3,

    "status": "task_assigned",
}


# ---------------------------------------------------------
# Run Assessment → Review → Regeneration cycle
# ---------------------------------------------------------

result = run_assessment_cycle(
    state=state,
    registry=registry,
    max_attempts=3,
)


# ---------------------------------------------------------
# Show result
# ---------------------------------------------------------

print("\n========================================")
print("ASSESSMENT CYCLE RESULT")
print("========================================")

print(
    "Status:",
    result.get("status")
)

print(
    "Review Status:",
    result.get(
        "assessment_review_status"
    )
)

print(
    "Attempts:",
    result.get(
        "assessment_review_attempts"
    )
)

print(
    "Max Attempts:",
    result.get(
        "assessment_max_review_attempts"
    )
)

print(
    "Review Feedback:",
    result.get(
        "assessment_review_feedback",
        ""
    )
)


# ---------------------------------------------------------
# Show generated questions
# ---------------------------------------------------------

questions = result.get(
    "questions",
    []
)

print(
    "\nQuestions:",
    len(questions)
)

for q in questions:

    print(
        f"\nQ{q['question_number']}: "
        f"{q['question']}"
    )

    for index, option in enumerate(
        q["options"],
        start=1,
    ):
        print(
            f"  {index}. {option}"
        )

    print(
        "Correct:",
        q["correct_option"]
    )

    print(
        "Marks:",
        q["marks"]
    )


# ---------------------------------------------------------
# Final status
# ---------------------------------------------------------

if result.get(
    "assessment_review_status"
) == "passed":

    print(
        "\n✅ ASSESSMENT CYCLE PASSED"
    )

elif result.get(
    "status"
) == "assessment_review_failed":

    print(
        "\n⚠️ ASSESSMENT FAILED AFTER MAX ATTEMPTS"
    )

else:

    print(
        "\n❌ ASSESSMENT CYCLE ERROR"
    )

    print(
        "Error Code:",
        result.get("error_code")
    )

    print(
        "Error:",
        result.get("error_message")
    )