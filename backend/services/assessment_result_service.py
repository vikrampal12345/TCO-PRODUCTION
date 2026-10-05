from __future__ import annotations

import json
from typing import Any

from backend.services.result_store import (
    ResultStore,
    ResultStoreError,
)
from backend.services.student_identity import (
    StudentIdentityError,
    StudentIdentityResolver,
)


class AssessmentResultServiceError(RuntimeError):
    """Raised when the evaluated result cannot be finalized and saved."""


class AssessmentResultService:
    """
    Bridge between evaluation, student identity, and result persistence.

    Flow:

        Evaluation Agent
                ↓
        Student Identity Resolver
                ↓
        ResultStore
                ↓
        Saved Result

    Responsibilities:
        - Validate evaluated result.
        - Resolve the student.
        - Persist the final result.

    Does NOT:
        - evaluate answers
        - generate questions
        - fetch Google Forms responses
        - perform OCR
        - send result emails
        - contain LLM logic
    """

    def __init__(
        self,
        *,
        result_store: ResultStore | None = None,
        identity_resolver: StudentIdentityResolver | None = None,
    ) -> None:
        self.result_store = (
            result_store
            or ResultStore()
        )

        self.identity_resolver = (
            identity_resolver
            or StudentIdentityResolver()
        )

    # =========================================================
    # VALIDATION
    # =========================================================

    @staticmethod
    def _require_assessment_id(
        assessment_id: int,
    ) -> int:
        try:
            assessment_id = int(
                assessment_id
            )
        except (TypeError, ValueError) as exc:
            raise AssessmentResultServiceError(
                "assessment_id must be an integer."
            ) from exc

        if assessment_id <= 0:
            raise AssessmentResultServiceError(
                "assessment_id must be greater than 0."
            )

        return assessment_id

    @staticmethod
    def _require_complete_evaluation(
        evaluation_result: dict[str, Any],
    ) -> None:
        if not isinstance(
            evaluation_result,
            dict,
        ):
            raise AssessmentResultServiceError(
                "evaluation_result must be a dictionary."
            )

        review_required = bool(
            evaluation_result.get(
                "review_required",
                False,
            )
        )

        evaluation_status = str(
            evaluation_result.get(
                "evaluation_status",
                "",
            )
        ).strip().lower()

        if review_required:
            raise AssessmentResultServiceError(
                "Evaluation requires review and cannot be saved "
                "as a final result."
            )

        if evaluation_status == "requires_review":
            raise AssessmentResultServiceError(
                "Evaluation status is requires_review and cannot "
                "be saved as a final result."
            )

    # =========================================================
    # SAVE ONE EVALUATED RESULT
    # =========================================================

    def save_evaluated_result(
        self,
        *,
        assessment_id: int,
        evaluation_result: dict[str, Any],
        student_id: int | None = None,
        student_no: str | None = None,
        university_roll: str | None = None,
        student_email: str | None = None,
        student_name: str | None = None,
        school_id: str | None = None,
        class_level: str | None = None,
        section: str | None = None,
        attempt_number: int = 1,
        started_at: str | None = None,
    ) -> dict[str, Any]:
        """
        Resolve the student and persist one finalized evaluation.

        Identity can come from:
            - explicit method arguments
            - evaluation_result fields

        Identity precedence is handled by StudentIdentityResolver.
        """

        assessment_id = (
            self._require_assessment_id(
                assessment_id
            )
        )

        self._require_complete_evaluation(
            evaluation_result
        )

        # -----------------------------------------------------
        # Identity data
        #
        # Explicit arguments take priority.
        # Missing values are taken from evaluation_result.
        # -----------------------------------------------------

        resolved_student_id = (
            student_id
            if student_id is not None
            else evaluation_result.get(
                "student_id"
            )
        )

        resolved_student_email = (
            student_email
            if student_email is not None
            else evaluation_result.get(
                "student_email"
            )
        )

        resolved_student_name = (
            student_name
            if student_name is not None
            else evaluation_result.get(
                "student_name"
            )
        )

        # -----------------------------------------------------
        # Resolve student identity
        # -----------------------------------------------------

        try:
            identity_result = (
                self.identity_resolver.resolve(
                    student_id=resolved_student_id,
                    student_no=student_no,
                    university_roll=university_roll,
                    email=resolved_student_email,
                    name=resolved_student_name,
                    school_id=school_id,
                    class_level=class_level,
                    section=section,
                )
            )

        except StudentIdentityError as exc:
            raise AssessmentResultServiceError(
                f"Student identity validation failed: {exc}"
            ) from exc

        identity_status = identity_result.get(
            "status"
        )

        # -----------------------------------------------------
        # No match
        # -----------------------------------------------------

        if identity_status == "not_found":
            raise AssessmentResultServiceError(
                "Student could not be identified. "
                "Result was not saved."
            )

        # -----------------------------------------------------
        # Ambiguous match
        # -----------------------------------------------------

        if identity_status == "ambiguous":
            raise AssessmentResultServiceError(
                "Student identity is ambiguous. "
                "A stronger identifier is required. "
                f"Candidates: "
                f"{identity_result.get('match_count', 0)}"
            )

        # -----------------------------------------------------
        # Unexpected identity response
        # -----------------------------------------------------

        if identity_status != "matched":
            raise AssessmentResultServiceError(
                "Student identity resolution returned an "
                f"unexpected status: {identity_status}"
            )

        student = identity_result.get(
            "student"
        )

        if not student:
            raise AssessmentResultServiceError(
                "Student identity matched but no student record "
                "was returned."
            )

        # -----------------------------------------------------
        # Evaluation values
        # -----------------------------------------------------

        obtained_marks = float(
            evaluation_result.get(
                "obtained_marks",
                0,
            )
        )

        total_marks = float(
            evaluation_result.get(
                "total_marks",
                0,
            )
        )

        correct_answers = int(
            evaluation_result.get(
                "correct_answers",
                0,
            )
        )

        wrong_answers = int(
            evaluation_result.get(
                "wrong_answers",
                0,
            )
        )

        unanswered = int(
            evaluation_result.get(
                "unanswered",
                0,
            )
        )

        submitted_at = (
            evaluation_result.get(
                "submitted_at"
            )
        )

        form_response_id = (
            evaluation_result.get(
                "response_id"
            )
            or evaluation_result.get(
                "submission_id"
            )
        )

        # -----------------------------------------------------
        # Persist question-level evaluation details.
        #
        # We keep the question-wise result JSON in ResultStore
        # so the original evaluation detail is not lost.
        # -----------------------------------------------------

        question_results = (
            evaluation_result.get(
                "question_results",
                [],
            )
            or []
        )

        question_results_json = json.dumps(
            question_results,
            ensure_ascii=False,
        )

        # The current Evaluation Agent does not always carry
        # the raw normalized answers in its final result.
        # Therefore answers_json remains optional here.
        answers = evaluation_result.get(
            "answers"
        )

        answers_json = (
            json.dumps(
                answers,
                ensure_ascii=False,
            )
            if answers is not None
            else None
        )

        # -----------------------------------------------------
        # Result status
        # -----------------------------------------------------

        result_status = (
            "evaluated"
        )

        try:
            saved_result = (
                self.result_store.save_result(
                    assessment_id=assessment_id,
                    student_id=int(
                        student["student_id"]
                    ),
                    obtained_marks=obtained_marks,
                    total_marks=total_marks,
                    correct_answers=correct_answers,
                    wrong_answers=wrong_answers,
                    unanswered=unanswered,
                    submitted_at=submitted_at,
                    started_at=started_at,
                    form_response_id=form_response_id,
                    answers_json=answers_json,
                    question_results_json=(
                        question_results_json
                    ),
                    status=result_status,
                    attempt_number=attempt_number,
                )
            )

        except ResultStoreError as exc:
            raise AssessmentResultServiceError(
                f"ResultStore failed to save result: {exc}"
            ) from exc

        # -----------------------------------------------------
        # Final response
        # -----------------------------------------------------

        return {
            "status": "saved",
            "identity_method": (
                identity_result.get(
                    "method"
                )
            ),
            "student": student,
            "evaluation": evaluation_result,
            "saved_result": saved_result,
        }


__all__ = [
    "AssessmentResultService",
    "AssessmentResultServiceError",
]