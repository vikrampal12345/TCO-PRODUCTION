from typing import Any

from backend.agents.assessment_review_agent import AssessmentReviewAgent
from backend.core.registry import ComponentRegistry
from backend.core.task import Task
from backend.core.task_executor import execute_task
from backend.core.task_router import TaskRouter
from backend.agents.assessment_agent import AssessmentAgent
from backend.state import TCOState


class AssessmentCycleService:
    """
    Coordinates the Assessment Agent and Assessment Review Agent.

    Flow:

        Assessment Agent
              ↓
        Review Agent
          ↙       ↘
       FAIL       PASS
        ↓           ↓
    Regenerate   Teacher Approval

    This service coordinates the cycle.
    It does NOT generate questions or perform the review itself.
    """

    DEFAULT_MAX_ATTEMPTS = 3

    def __init__(
        self,
        registry: ComponentRegistry,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ):
        if max_attempts < 1:
            raise ValueError(
                "max_attempts must be at least 1."
            )

        self.registry = registry
        self.router = TaskRouter(registry)
        self.max_attempts = max_attempts

    def run(
        self,
        state: TCOState,
    ) -> TCOState:
        """
        Run the assessment generation/review cycle.
        """

        attempts = int(
            state.get(
                "assessment_review_attempts",
                0,
            )
        )

        max_attempts = int(
            state.get(
                "assessment_max_review_attempts",
                self.max_attempts,
            )
        )

        while attempts < max_attempts:

            attempts += 1

            # -------------------------------------------------
            # Generate
            # -------------------------------------------------

            assessment_task = self._create_assessment_task(
                state=state,
                attempt=attempts,
            )

            assessment_provider, assessment_task = (
                self.router.route(
                    assessment_task
                )
            )

            state = execute_task(
                provider=assessment_provider,
                task=assessment_task,
                state={
                    **state,
                    "assessment_review_attempts": attempts,
                    "assessment_max_review_attempts": max_attempts,
                },
            )

            # Generation itself failed.
            if state.get("status") == "error":
                return state

            # -------------------------------------------------
            # Review
            # -------------------------------------------------

            review_task = Task(
                capability="assessment.review",
                input_data={
                    "assessment_task_id": (
                        assessment_task.task_id
                    ),
                    "attempt": attempts,
                },
                metadata={
                    "request_id": state.get(
                        "request_id"
                    ),
                },
            )

            review_provider, review_task = (
                self.router.route(
                    review_task
                )
            )

            state = execute_task(
                provider=review_provider,
                task=review_task,
                state=state,
            )

            if state.get("status") == "error":
                return state

            # -------------------------------------------------
            # Review PASSED
            # -------------------------------------------------

            if (
                state.get(
                    "assessment_review_status"
                )
                == "passed"
            ):
                return {
                    **state,
                    "assessment_review_attempts": attempts,
                    "assessment_max_review_attempts": max_attempts,
                    "approval_required": True,
                    "approval_type": "assessment",
                    "approval_status": "pending",
                    "status": "assessment_ready_for_teacher",
                }

            # -------------------------------------------------
            # Review FAILED
            # -------------------------------------------------

            if (
                state.get(
                    "assessment_review_status"
                )
                == "failed"
            ):

                if attempts >= max_attempts:

                    return {
                        **state,
                        "assessment_review_attempts": attempts,
                        "assessment_max_review_attempts": max_attempts,
                        "approval_required": False,
                        "approval_status": "not_ready",
                        "status": (
                            "assessment_review_failed"
                        ),
                        "error_code": (
                            "ASSESSMENT_MAX_ATTEMPTS_REACHED"
                        ),
                        "error_message": (
                            f"Assessment failed review "
                            f"after {max_attempts} attempts."
                        ),
                    }

                # Feed reviewer feedback into the next
                # Assessment Agent attempt.
                state = {
                    **state,
                    "status": (
                        "assessment_regenerating"
                    ),
                }

                continue

            # -------------------------------------------------
            # Unexpected review status
            # -------------------------------------------------

            return {
                **state,
                "status": "error",
                "error_code": (
                    "INVALID_ASSESSMENT_REVIEW_STATUS"
                ),
                "error_message": (
                    "Assessment review returned an "
                    "unexpected status."
                ),
            }

        return {
            **state,
            "status": "assessment_review_failed",
            "error_code": (
                "ASSESSMENT_MAX_ATTEMPTS_REACHED"
            ),
        }

    # ---------------------------------------------------------
    # TASK CREATION
    # ---------------------------------------------------------

    def _create_assessment_task(
        self,
        state: TCOState,
        attempt: int,
    ) -> Task:
        """
        Create an assessment-generation task.

        Reviewer feedback from the previous attempt is passed
        to the Assessment Agent as task input.
        """

        previous_feedback = (
            state.get(
                "assessment_review_feedback",
                "",
            )
            or ""
        )

        return Task(
            capability="assessment.create",
            input_data={
                "teacher_request": state.get(
                    "teacher_request"
                ),

                "class_level": state.get(
                    "class_level"
                ),

                "subject": state.get(
                    "subject"
                ),

                "chapter": state.get(
                    "chapter"
                ),

                "topic": state.get(
                    "topic"
                ),

                "student_name": state.get(
                    "student_name"
                ),

                "marks": state.get(
                    "marks"
                ),

                "question_count": state.get(
                    "question_count"
                ),

                "generation_mode": state.get(
                    "generation_mode",
                    "source_grounded",
                ),

                "requested_source": state.get(
                    "requested_source"
                ),

                "source_preference": state.get(
                    "source_preference"
                ),

                "source_url": state.get(
                    "source"
                ),

                "review_feedback": previous_feedback,

                "attempt": attempt,
            },
            metadata={
                "request_id": state.get(
                    "request_id"
                ),
                "teacher_id": state.get(
                    "teacher_id"
                ),
                "conversation_id": state.get(
                    "conversation_id"
                ),
                "attempt": attempt,
            },
        )


def run_assessment_cycle(
    state: TCOState,
    registry: ComponentRegistry,
    max_attempts: int = 3,
) -> TCOState:
    """
    Convenience function for the assessment cycle.
    """

    return AssessmentCycleService(
        registry=registry,
        max_attempts=max_attempts,
    ).run(state)