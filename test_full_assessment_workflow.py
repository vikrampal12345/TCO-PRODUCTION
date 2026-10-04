from backend.core.bootstrap import build_default_registry
from backend.workflows.assessment_delivery import (
    AssessmentDeliveryWorkflow,
)


# ============================================================
# TEST CONFIGURATION
# ============================================================

TEACHER_ID = "teacher-demo"

# This is the TEST cohort already created in your SQLite DB.
SCHOOL_ID = "TCO_TEST"
STUDENT_CLASS = "TCO Test Class"
STUDENT_SECTION = "TEST"


# ============================================================
# ASSESSMENT REQUEST
# ============================================================

state = {
    "request_id": "workflow_test_001",

    "teacher_id": TEACHER_ID,
    "school_id": SCHOOL_ID,

    "teacher_request": (
        "Create a 5-question, 5-mark MCQ assessment "
        "on Python basics using AI general knowledge."
    ),

    "intent": "assessment",
    "language": "english",

    "required_capability": "assessment.create",

    "class_level": "BTech 1st Year",
    "subject": "Python",
    "chapter": "Python Basics",
    "topic": "Python Basics",

    "marks": 5,
    "question_count": 5,

    # Explicitly allow local LLM general knowledge.
    "generation_mode": "llm_generated",

    "requested_source": "",
    "source_preference": "general_knowledge",
    "source_url": "",

    "section": STUDENT_SECTION,

    "missing_information": [],

    "status": "starting",
}


# ============================================================
# BUILD REGISTRY
# ============================================================

print("\n========================================")
print("TCO END-TO-END ASSESSMENT WORKFLOW")
print("========================================")

print("\nBuilding registry...")

registry = build_default_registry()

print("Registry ready.")


# ============================================================
# BUILD WORKFLOW
# ============================================================

workflow = AssessmentDeliveryWorkflow(
    registry=registry,
    max_review_attempts=3,
)


# ============================================================
# RUN
# ============================================================

final_state = workflow.run(
    state,
    teacher_id=TEACHER_ID,
    school_id=SCHOOL_ID,
    student_class_level=STUDENT_CLASS,
    student_section=STUDENT_SECTION,
)


# ============================================================
# FINAL RESULT
# ============================================================

print("\n========================================")
print("FINAL WORKFLOW RESULT")
print("========================================")

print(
    "Status:",
    final_state.get("status"),
)

print(
    "Review Status:",
    final_state.get(
        "assessment_review_status"
    ),
)

print(
    "Review Attempts:",
    final_state.get(
        "assessment_review_attempts"
    ),
)

print(
    "Assessment ID:",
    final_state.get(
        "assessment_id"
    ),
)

print(
    "Google Form ID:",
    final_state.get(
        "form_id"
    ),
)

print(
    "Responder URL:",
    final_state.get(
        "responder_url"
    ),
)

print(
    "Published:",
    final_state.get(
        "form_is_published"
    ),
)

print(
    "Accepting Responses:",
    final_state.get(
        "form_accepting_responses"
    ),
)

print(
    "Emails Sent:",
    final_state.get(
        "student_email_sent"
    ),
)

print(
    "Emails Failed:",
    final_state.get(
        "student_email_failed"
    ),
)


if final_state.get("error_code"):

    print(
        "\nError Code:",
        final_state.get(
            "error_code"
        ),
    )

    print(
        "Error Message:",
        final_state.get(
            "error_message"
        ),
    )


print("\n========================================")
print("WORKFLOW TEST FINISHED")
print("========================================")