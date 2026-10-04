from typing import Any

from backend.state import TCOState


class AssessmentApprovalError(Exception):
    """Raised when assessment approval cannot be processed."""


class AssessmentApprovalService:
    """
    Handles the final teacher decision on a reviewed assessment.

    The Review Agent checks quality.
    The Teacher gives the final approval.

    This service does not generate or review questions.
    """

    def approve(
        self,
        state: TCOState,
        approved_by: str,
        comment: str = "",
    ) -> TCOState:
        """
        Approve an assessment after the Review Agent has passed it.
        """

        if (
            state.get("assessment_review_status")
            != "passed"
        ):
            raise AssessmentApprovalError(
                "Assessment cannot be approved before "
                "the Review Agent passes it."
            )

        if not approved_by.strip():
            raise AssessmentApprovalError(
                "approved_by is required."
            )

        return {
            **state,

            "approval_required": False,

            "approval_type": "assessment",

            "approval_status": "approved",

            "approved_by": approved_by.strip(),

            "approval_comment": comment.strip(),

            "status": "assessment_approved",

            "metadata": {
                **state.get("metadata", {}),
                "assessment_approval": {
                    "approved_by": approved_by.strip(),
                    "comment": comment.strip(),
                },
            },
        }

    def reject(
        self,
        state: TCOState,
        rejected_by: str,
        feedback: str,
    ) -> TCOState:
        """
        Reject the assessment and send teacher feedback
        back into the regeneration workflow.
        """

        if (
            state.get("assessment_review_status")
            != "passed"
        ):
            raise AssessmentApprovalError(
                "Assessment cannot be rejected through the "
                "teacher-review stage because it has not "
                "passed the Review Agent."
            )

        if not rejected_by.strip():
            raise AssessmentApprovalError(
                "rejected_by is required."
            )

        if not feedback.strip():
            raise AssessmentApprovalError(
                "Teacher feedback is required when "
                "rejecting an assessment."
            )

        return {
            **state,

            "approval_required": False,

            "approval_type": "assessment",

            "approval_status": "rejected",

            "approved_by": rejected_by.strip(),

            "approval_comment": feedback.strip(),

            # Reuse the same feedback channel that the
            # Assessment Agent already understands.
            "assessment_review_feedback": (
                feedback.strip()
            ),

            "status": (
                "assessment_needs_regeneration"
            ),

            "metadata": {
                **state.get("metadata", {}),
                "assessment_teacher_rejection": {
                    "rejected_by": rejected_by.strip(),
                    "feedback": feedback.strip(),
                },
            },
        }


def approve_assessment(
    state: TCOState,
    approved_by: str,
    comment: str = "",
) -> TCOState:
    """Convenience function for assessment approval."""

    return AssessmentApprovalService().approve(
        state=state,
        approved_by=approved_by,
        comment=comment,
    )


def reject_assessment(
    state: TCOState,
    rejected_by: str,
    feedback: str,
) -> TCOState:
    """Convenience function for assessment rejection."""

    return AssessmentApprovalService().reject(
        state=state,
        rejected_by=rejected_by,
        feedback=feedback,
    )