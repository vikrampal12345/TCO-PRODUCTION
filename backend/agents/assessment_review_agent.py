from typing import Any

from backend.core.base_agent import BaseAgent
from backend.core.model_provider import get_chat_model
from backend.core.task import Task
from backend.schemas.assessment_review import (
    AssessmentReview,
)
from backend.state import TCOState


ASSESSMENT_REVIEW_PROMPT = """
You are the Assessment Review Agent of TCO.

Your job is to independently review an MCQ assessment
created by the Assessment Agent.

You are NOT the question generator.

You must critically verify every question.

==================================================
CHECK EACH QUESTION
==================================================

For every MCQ verify:

1. The question is relevant to the requested topic.
2. The question is appropriate for the requested class.
3. There are exactly four options.
4. Exactly one option is correct.
5. The claimed correct option is actually correct.
6. The question is not ambiguous.
7. There are no duplicate or near-duplicate questions.
8. The answer is supported by the provided source
   when source-grounded mode is being used.

Do NOT approve a question merely because the
Assessment Agent claims an option is correct.

Independently reason about the answer.

==================================================
SOURCE-GROUNDED MODE
==================================================

When generation_mode = source_grounded:

Use the provided source material as the
primary authority.

Do not approve claims that are unsupported
by the supplied source material.

==================================================
AI-GENERATED MODE
==================================================

When generation_mode = llm_generated:

General knowledge may be used because the
teacher explicitly allowed it.

==================================================
APPROVAL RULE
==================================================

Approve the assessment ONLY when all questions
are acceptable.

If even one question has a significant problem:

approved = false

Clearly explain:
- which question is wrong
- what is wrong
- how it should be corrected

==================================================
IMPORTANT
==================================================

Do not rewrite the complete assessment.

Return only the structured review.
"""


class AssessmentReviewAgent(BaseAgent):

    name = "assessment_review_agent"

    description = (
        "Independently verifies generated MCQ assessments "
        "before teacher approval."
    )

    capabilities = (
        "assessment.review",
    )

    def __init__(self):
        self.model = get_chat_model().with_structured_output(
            AssessmentReview
        )

    # ---------------------------------------------------------
    # MAIN
    # ---------------------------------------------------------

    def run(
        self,
        state: TCOState,
        task: Task | None = None,
    ) -> TCOState:

        questions = state.get(
            "questions",
            []
        )

        if not questions:
            return {
                **state,
                "status": "error",
                "error_code": "ASSESSMENT_REVIEW_INPUT_MISSING",
                "error_message": (
                    "No generated assessment is available "
                    "for review."
                ),
            }

        topic = (
            state.get("topic")
            or state.get("chapter")
            or ""
        )

        class_level = (
            state.get("class_level")
            or ""
        )

        subject = (
            state.get("subject")
            or ""
        )

        generation_mode = state.get(
            "generation_mode",
            "source_grounded",
        )

        retrieved_context = (
            state.get(
                "retrieved_context",
                "",
            )
            or ""
        ).strip()

        # -----------------------------------------------------
        # Deterministic structural validation
        # -----------------------------------------------------

        structural_errors = (
            self._validate_structure(
                questions=questions,
                expected_count=state.get(
                    "question_count"
                ),
            )
        )

        # -----------------------------------------------------
        # Build question content for reviewer
        # -----------------------------------------------------

        questions_text = self._format_questions(
            questions
        )

        source_section = ""

        if generation_mode == "source_grounded":

            source_section = f"""
==================================================
SOURCE MATERIAL
==================================================

{retrieved_context}

==================================================
END SOURCE MATERIAL
==================================================
"""

        prompt = f"""
{ASSESSMENT_REVIEW_PROMPT}

==================================================
ASSESSMENT CONTEXT
==================================================

Topic:
{topic}

Subject:
{subject}

Class:
{class_level}

Generation Mode:
{generation_mode}

==================================================
GENERATED ASSESSMENT
==================================================

{questions_text}

{source_section}

==================================================
STRUCTURAL VALIDATION
==================================================

{self._format_errors(structural_errors)}

Now independently review every question.
"""

        # -----------------------------------------------------
        # LLM review
        # -----------------------------------------------------

        try:
            review: AssessmentReview = self.model.invoke(
                prompt
            )

        except Exception as exc:
            return {
                **state,
                "status": "error",
                "error_code": "ASSESSMENT_REVIEW_FAILED",
                "error_message": str(exc),
            }

        # -----------------------------------------------------
        # Combine deterministic + semantic review
        # -----------------------------------------------------

        final_issues = list(
            structural_errors
        )

        final_issues.extend(
            issue
            for issue in review.issues
            if issue.strip()
        )

        approved = (
            review.approved
            and not structural_errors
        )

        if not approved:

            feedback_parts = []

            if final_issues:
                feedback_parts.append(
                    "General issues:\n"
                    + "\n".join(
                        f"- {issue}"
                        for issue in final_issues
                    )
                )

            for question_review in (
                review.question_reviews
            ):
                if not question_review.correct:

                    feedback_parts.append(
                        f"Question "
                        f"{question_review.question_number}: "
                        f"{question_review.issue}"
                    )

                    if (
                        question_review
                        .suggested_correction
                    ):
                        feedback_parts.append(
                            "Correction: "
                            + question_review
                            .suggested_correction
                        )

            feedback = "\n".join(
                feedback_parts
            ).strip()

            return {
                **state,

                "assessment_review_status": "failed",

                "assessment_review_feedback": (
                    feedback
                    or review.summary
                    or "Assessment requires correction."
                ),

                "approval_required": False,

                "approval_status": "not_ready",

                "status": (
                    "assessment_needs_regeneration"
                ),

                "validation_status": "failed",

                "validation_errors": final_issues,
            }

        # -----------------------------------------------------
        # Approved by review agent
        # -----------------------------------------------------

        return {
            **state,

            "assessment_review_status": "passed",

            "assessment_review_feedback": (
                review.summary
            ),

            "approval_required": True,

            "approval_type": "assessment",

            "approval_status": "pending",

            "status": (
                "assessment_ready_for_teacher"
            ),

            "validation_status": "passed",

            "validation_errors": [],
        }

    # ---------------------------------------------------------
    # STRUCTURAL VALIDATION
    # ---------------------------------------------------------

    @staticmethod
    def _validate_structure(
        questions: list,
        expected_count: int | None,
    ) -> list[str]:

        errors: list[str] = []

        if (
            expected_count is not None
            and len(questions) != expected_count
        ):
            errors.append(
                f"Expected {expected_count} questions "
                f"but received {len(questions)}."
            )

        seen: set[str] = set()

        for index, question in enumerate(
            questions,
            start=1,
        ):

            options = question.get(
                "options",
                []
            )

            if len(options) != 4:
                errors.append(
                    f"Question {index} must contain "
                    f"exactly 4 options."
                )

            normalized_options = [
                str(option).strip().lower()
                for option in options
            ]

            if len(
                set(normalized_options)
            ) != len(normalized_options):
                errors.append(
                    f"Question {index} contains "
                    f"duplicate options."
                )

            correct_option = question.get(
                "correct_option"
            )

            if not isinstance(
                correct_option,
                int,
            ) or not 1 <= correct_option <= 4:
                errors.append(
                    f"Question {index} has an invalid "
                    f"correct option."
                )

            question_text = str(
                question.get(
                    "question",
                    ""
                )
            ).strip()

            if not question_text:
                errors.append(
                    f"Question {index} is empty."
                )

            normalized_question = (
                " ".join(
                    question_text
                    .lower()
                    .split()
                )
            )

            if normalized_question in seen:
                errors.append(
                    f"Question {index} is a duplicate."
                )

            seen.add(
                normalized_question
            )

        return errors

    # ---------------------------------------------------------
    # FORMAT HELPERS
    # ---------------------------------------------------------

    @staticmethod
    def _format_questions(
        questions: list,
    ) -> str:

        lines = []

        for question in questions:

            number = question.get(
                "question_number"
            )

            text = question.get(
                "question",
                ""
            )

            correct_option = question.get(
                "correct_option"
            )

            lines.append(
                f"Question {number}: {text}"
            )

            for index, option in enumerate(
                question.get(
                    "options",
                    []
                ),
                start=1,
            ):
                lines.append(
                    f"  {index}. {option}"
                )

            lines.append(
                f"Claimed correct option: "
                f"{correct_option}"
            )

            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _format_errors(
        errors: list[str],
    ) -> str:

        if not errors:
            return "No structural errors found."

        return "\n".join(
            f"- {error}"
            for error in errors
        )


# ============================================================
# BACKWARD-COMPATIBLE FUNCTION
# ============================================================

_assessment_review_agent = AssessmentReviewAgent()


def assessment_review_agent(
    state: TCOState,
    task: Task | None = None,
) -> TCOState:

    return _assessment_review_agent.run(
        state,
        task,
    )