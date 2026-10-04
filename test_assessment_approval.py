from backend.services.assessment_approval import (
    approve_assessment,
    reject_assessment,
)


base_state = {
    "assessment_review_status": "passed",
    "assessment_review_attempts": 1,
    "status": "assessment_ready_for_teacher",
    "metadata": {},
}


# ---------------------------------------------------------
# TEST 1: Teacher approves
# ---------------------------------------------------------

approved_state = approve_assessment(
    state=base_state,
    approved_by="teacher_001",
    comment="Questions look good.",
)

print("TEST 1")
print(
    "Approval:",
    approved_state["approval_status"],
)

print(
    "Status:",
    approved_state["status"],
)


# ---------------------------------------------------------
# TEST 2: Teacher rejects
# ---------------------------------------------------------

rejected_state = reject_assessment(
    state=base_state,
    rejected_by="teacher_001",
    feedback=(
        "Question 3 is too easy. "
        "Replace it with a conceptual question."
    ),
)

print("\nTEST 2")
print(
    "Approval:",
    rejected_state["approval_status"],
)

print(
    "Status:",
    rejected_state["status"],
)

print(
    "Feedback:",
    rejected_state[
        "assessment_review_feedback"
    ],
)


print("\nASSESSMENT APPROVAL TEST PASSED")