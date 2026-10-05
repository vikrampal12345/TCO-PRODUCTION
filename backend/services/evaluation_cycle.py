from __future__ import annotations

from typing import Any

from backend.agents.evaluation_agent import EvaluationAgent
from backend.services.assessment_result_service import (
    AssessmentResultService,
    AssessmentResultServiceError,
)
from backend.tools.google_forms_metadata import GoogleFormsMetadataTool
from backend.tools.google_forms_responses import GoogleFormsResponsesTool


class EvaluationCycleError(RuntimeError):
    """Raised when the form evaluation cycle cannot continue."""


class EvaluationCycleService:
    """
    Orchestrates the Google Forms evaluation lifecycle.

    Evaluation-only flow:
        Google Forms metadata
            -> Google Forms responses
            -> identity/assessment separation
            -> Evaluation Agent
            -> evaluation result

    Evaluation + persistence flow:
        evaluation result
            -> AssessmentResultService
            -> StudentIdentityResolver
            -> ResultStore

    This service does NOT directly:
        - resolve students in the database
        - write to the database
        - send result emails
        - perform OCR / scan processing

    Student identity resolution and result persistence are delegated
    to AssessmentResultService.
    """

    def __init__(
        self,
        *,
        metadata_tool: GoogleFormsMetadataTool | None = None,
        response_tool: GoogleFormsResponsesTool | None = None,
        evaluation_agent: EvaluationAgent | None = None,
        result_service: AssessmentResultService | None = None,
    ) -> None:
        self.metadata_tool = (
            metadata_tool or GoogleFormsMetadataTool()
        )

        self.response_tool = (
            response_tool or GoogleFormsResponsesTool()
        )

        self.evaluation_agent = (
            evaluation_agent or EvaluationAgent()
        )

        self.result_service = result_service

    # ========================================================
    # PUBLIC: EVALUATE ALL FORM RESPONSES
    # ========================================================

    def evaluate_form(
        self,
        *,
        form_id: str,
        page_size: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Retrieve form metadata + all responses and evaluate them.

        No database write occurs here.

        Student identity fields are extracted before evaluation
        and are NOT sent to the Evaluation Agent as assessment
        answers.
        """

        form_id = str(form_id or "").strip()

        if not form_id:
            raise EvaluationCycleError("form_id is required.")

        metadata = self._get_form_metadata(form_id=form_id)

        questions = metadata.get("questions", []) or []
        answer_key = metadata.get("answer_key", []) or []
        marking_scheme = metadata.get("marking_scheme", []) or []
        identity_fields = metadata.get("identity_fields", []) or []

        if not questions:
            raise EvaluationCycleError(
                "Google Form contains no supported "
                "assessment question items."
            )

        responses = self._get_form_responses(
            form_id=form_id,
            page_size=page_size,
        )

        evaluation_results: list[dict[str, Any]] = []

        for response in responses:
            submission = self._build_submission(
                response=response,
                identity_fields=identity_fields,
            )

            evaluation_state = self.evaluation_agent.run(
                {
                    "questions": questions,
                    "answer_key": answer_key,
                    "marking_scheme": marking_scheme,
                    "current_submission": submission,
                    "submission_source": "google_forms",
                }
            )

            status = evaluation_state.get("status")

            if status not in {
                "evaluation_complete",
                "evaluation_requires_review",
            }:
                raise EvaluationCycleError(
                    "Evaluation Agent failed for response "
                    f"{response.get('response_id')}: "
                    f"{evaluation_state.get('error_message', 'unknown error')}"
                )

            result = dict(
                evaluation_state.get(
                    "evaluation_result",
                    {},
                )
            )

            result["form_id"] = form_id
            result["response_id"] = response.get("response_id")
            result["form_title"] = metadata.get("title")

            # Identity captured from the submitted form.
            # This is NOT database identity resolution.
            result["student_identifier"] = submission.get(
                "student_identifier"
            )
            result["student_email"] = submission.get(
                "student_email"
            )
            result["student_name"] = submission.get(
                "student_name"
            )
            result["submitted_at"] = submission.get(
                "submitted_at"
            )
            result["identity_field"] = submission.get(
                "identity_field"
            )
            result["identity_status"] = (
                "captured"
                if submission.get("student_identifier")
                else "missing"
            )

            # Preserve the normalized assessment answers so that
            # AssessmentResultService can optionally persist them.
            result["answers"] = submission.get("answers", [])

            evaluation_results.append(result)

        return evaluation_results

    # ========================================================
    # PUBLIC: EVALUATE ONE RESPONSE
    # ========================================================

    def evaluate_response(
        self,
        *,
        form_id: str,
        response_id: str,
        page_size: int = 100,
    ) -> dict[str, Any]:
        """
        Evaluate one specific response.

        The established cycle lists responses and selects the
        requested response by ID.
        """

        response_id = str(response_id or "").strip()

        if not response_id:
            raise EvaluationCycleError("response_id is required.")

        results = self.evaluate_form(
            form_id=form_id,
            page_size=page_size,
        )

        for result in results:
            if result.get("response_id") == response_id:
                return result

        raise EvaluationCycleError(
            "Response not found in the fetched "
            f"form responses: {response_id}"
        )

    # ========================================================
    # PUBLIC: EVALUATE + SAVE ALL RESPONSES
    # ========================================================

    def evaluate_and_save_form(
        self,
        *,
        form_id: str,
        assessment_id: int,
        school_id: str | None = None,
        class_level: str | None = None,
        section: str | None = None,
        attempt_number: int = 1,
        page_size: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Evaluate all form responses and persist finalized results.

        Flow:
            evaluate_form()
                -> AssessmentResultService.save_evaluated_result()

        Identity values are passed separately:
            student_identifier -> student_no
            student_email      -> student_email
            student_name       -> student_name

        AssessmentResultService remains responsible for actual
        student resolution and database persistence.
        """

        if self.result_service is None:
            raise EvaluationCycleError(
                "result_service is required for evaluate_and_save_form()."
            )

        evaluation_results = self.evaluate_form(
            form_id=form_id,
            page_size=page_size,
        )

        lifecycle_results: list[dict[str, Any]] = []

        for evaluation_result in evaluation_results:
            lifecycle_results.append(
                self._save_evaluation_result(
                    assessment_id=assessment_id,
                    evaluation_result=evaluation_result,
                    school_id=school_id,
                    class_level=class_level,
                    section=section,
                    attempt_number=attempt_number,
                )
            )

        return lifecycle_results

    # ========================================================
    # PUBLIC: EVALUATE + SAVE ONE RESPONSE
    # ========================================================

    def evaluate_and_save_response(
        self,
        *,
        form_id: str,
        response_id: str,
        assessment_id: int,
        school_id: str | None = None,
        class_level: str | None = None,
        section: str | None = None,
        attempt_number: int = 1,
        page_size: int = 100,
    ) -> dict[str, Any]:
        """
        Evaluate one response and persist its finalized result.
        """

        if self.result_service is None:
            raise EvaluationCycleError(
                "result_service is required for "
                "evaluate_and_save_response()."
            )

        evaluation_result = self.evaluate_response(
            form_id=form_id,
            response_id=response_id,
            page_size=page_size,
        )

        return self._save_evaluation_result(
            assessment_id=assessment_id,
            evaluation_result=evaluation_result,
            school_id=school_id,
            class_level=class_level,
            section=section,
            attempt_number=attempt_number,
        )

    # ========================================================
    # SAVE BRIDGE
    # ========================================================
    def _save_evaluation_result(
        self,
        *,
        assessment_id: int,
        evaluation_result: dict[str, Any],
        school_id: str | None,
        class_level: str | None,
        section: str | None,
        attempt_number: int,
    ) -> dict[str, Any]:
        """
        Pass one evaluation result to AssessmentResultService.

        Student identity failures are kept as per-response lifecycle
        statuses so one invalid/unknown student does not abort the
        complete form evaluation cycle.

        Genuine persistence failures remain fatal.
        """

        if self.result_service is None:
            raise EvaluationCycleError(
                "result_service is required."
            )

        # ----------------------------------------------------
        # Review-required evaluation
        # ----------------------------------------------------

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

        if review_required or evaluation_status in {
            "requires_review",
            "evaluation_requires_review",
        }:
            return {
                "status": "review_required",
                "response_id": evaluation_result.get(
                    "response_id"
                ),
                "evaluation": evaluation_result,
                "saved_result": None,
                "identity_method": None,
            }

        # ----------------------------------------------------
        # Identity captured from Google Form
        # ----------------------------------------------------

        student_identifier = evaluation_result.get(
            "student_identifier"
        )

        try:
            saved = self.result_service.save_evaluated_result(
                assessment_id=assessment_id,
                evaluation_result=evaluation_result,
                student_no=(
                    str(student_identifier).strip()
                    if student_identifier is not None
                    and str(student_identifier).strip()
                    else None
                ),
                student_email=evaluation_result.get(
                    "student_email"
                ),
                student_name=evaluation_result.get(
                    "student_name"
                ),
                school_id=school_id,
                class_level=class_level,
                section=section,
                attempt_number=attempt_number,
            )

        except AssessmentResultServiceError as exc:
            error_message = str(exc)

            # ------------------------------------------------
            # Student identity could not be resolved.
            #
            # This is a per-response failure, not a failure
            # of the complete form evaluation cycle.
            # ------------------------------------------------

            if (
                error_message
                == "Student could not be identified. "
                "Result was not saved."
            ):
                return {
                    "status": "identity_not_found",
                    "response_id": evaluation_result.get(
                        "response_id"
                    ),
                    "identity": {
                        "student_identifier": (
                            student_identifier
                        ),
                        "student_email": (
                            evaluation_result.get(
                                "student_email"
                            )
                        ),
                        "student_name": (
                            evaluation_result.get(
                                "student_name"
                            )
                        ),
                    },
                    "evaluation_result": evaluation_result,
                    "evaluation": evaluation_result,
                    "saved_result": None,
                    "identity_method": None,
                    "error": error_message,
                }

            # ------------------------------------------------
            # Ambiguous student identity.
            #
            # Also keep this as a per-response review state.
            # ------------------------------------------------

            if error_message.startswith(
                "Student identity is ambiguous."
            ):
                return {
                    "status": "identity_ambiguous",
                    "response_id": evaluation_result.get(
                        "response_id"
                    ),
                    "identity": {
                        "student_identifier": (
                            student_identifier
                        ),
                        "student_email": (
                            evaluation_result.get(
                                "student_email"
                            )
                        ),
                        "student_name": (
                            evaluation_result.get(
                                "student_name"
                            )
                        ),
                    },
                    "evaluation_result": evaluation_result,
                    "evaluation": evaluation_result,
                    "saved_result": None,
                    "identity_method": None,
                    "error": error_message,
                }

            # ------------------------------------------------
            # Any other AssessmentResultServiceError is a
            # genuine lifecycle failure and should still stop.
            # ------------------------------------------------

            raise EvaluationCycleError(
                "Failed to save evaluated result for response "
                f"{evaluation_result.get('response_id')}: "
                f"{exc}"
            ) from exc

        # ----------------------------------------------------
        # Successfully saved
        # ----------------------------------------------------

        return {
            "status": "saved",
            "response_id": evaluation_result.get(
                "response_id"
            ),
            "identity_method": saved.get(
                "identity_method"
            ),
            "evaluation_result": saved.get(
                "evaluation",
                evaluation_result,
            ),
            "evaluation": saved.get(
                "evaluation",
                evaluation_result,
            ),
            "saved_result": saved.get(
                "saved_result"
            ),
            "identity": saved.get(
                "student"
            ),
        }
    
    # ========================================================
    # METADATA
    # ========================================================

    def _get_form_metadata(
        self,
        *,
        form_id: str,
    ) -> dict[str, Any]:
        """Retrieve normalized Google Forms metadata."""

        metadata_result = self.metadata_tool.execute(
            operation="form.metadata.get",
            form_id=form_id,
        )

        if not metadata_result.success:
            raise EvaluationCycleError(
                "Form metadata retrieval failed: "
                f"{metadata_result.error_message}"
            )

        return metadata_result.data or {}

    # ========================================================
    # RESPONSES
    # ========================================================

    def _get_form_responses(
        self,
        *,
        form_id: str,
        page_size: int,
    ) -> list[dict[str, Any]]:
        """Retrieve normalized responses from Google Forms."""

        response_result = self.response_tool.execute(
            operation="form.responses.list",
            form_id=form_id,
            page_size=page_size,
        )

        if not response_result.success:
            raise EvaluationCycleError(
                "Form response retrieval failed: "
                f"{response_result.error_message}"
            )

        responses_data = response_result.data or {}

        return responses_data.get(
            "responses",
            [],
        ) or []

    # ========================================================
    # BUILD NORMALIZED SUBMISSION
    # ========================================================

    @classmethod
    def _build_submission(
        cls,
        *,
        response: dict[str, Any],
        identity_fields: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Separate identity answers from assessment answers.

        Identity mapping:

            student_name
                <- identity_type = "student_name"

            student_identifier
                <- identity_type =
                   "student_id_or_roll_number"

            student_email
                <- identity_type = "student_email"

        Identity answers are never sent to the
        Evaluation Agent as assessment answers.
        """

        identity_fields = identity_fields or []

        # ----------------------------------------------------
        # Build question-id -> identity descriptor mapping
        # ----------------------------------------------------

        identity_by_question_id: dict[str, dict[str, Any]] = {}

        for field in identity_fields:
            if not isinstance(field, dict):
                continue

            question_id = field.get("question_id")

            if not question_id:
                continue

            identity_by_question_id[
                str(question_id)
            ] = field

        # ----------------------------------------------------
        # Read submitted answers
        # ----------------------------------------------------

        raw_answers = (
            response.get("answers", [])
            or []
        )

        assessment_answers: list[dict[str, Any]] = []

        student_identifier: str | None = None
        student_name: str | None = None
        student_email: str | None = None

        captured_identity_fields: list[dict[str, Any]] = []

        for answer in raw_answers:
            if not isinstance(answer, dict):
                continue

            question_id = answer.get("question_id")

            if not question_id:
                continue

            question_id = str(question_id)

            values = (
                answer.get("values", [])
                or []
            )

            normalized_values = [
                str(value).strip()
                for value in values
                if value is not None
                and str(value).strip()
            ]

            # ------------------------------------------------
            # Identity answer
            # ------------------------------------------------

            identity_field = identity_by_question_id.get(
                question_id
            )

            if identity_field is not None:
                identity_type = identity_field.get(
                    "identity_type"
                )

                value = (
                    normalized_values[0]
                    if normalized_values
                    else None
                )

                if identity_type == "student_name":
                    student_name = value

                elif (
                    identity_type
                    == "student_id_or_roll_number"
                ):
                    student_identifier = value

                elif identity_type == "student_email":
                    student_email = value

                captured_identity_fields.append(
                    {
                        "field": identity_field,
                        "value": value,
                    }
                )

                # IMPORTANT:
                # Identity answers must never enter assessment answers.
                continue

            # ------------------------------------------------
            # Normal assessment answer
            # ------------------------------------------------

            assessment_answers.append(answer)

        # ----------------------------------------------------
        # Backward compatibility
        # ----------------------------------------------------
        #
        # Old forms / response sources may still provide
        # these values at response level.
        #
        # Explicit identity-question answers take priority.
        # ----------------------------------------------------

        if not student_email:
            respondent_email = response.get(
                "respondent_email"
            )

            if respondent_email:
                student_email = str(
                    respondent_email
                ).strip()

        if not student_name:
            response_name = response.get(
                "student_name"
            )

            if response_name:
                student_name = str(
                    response_name
                ).strip()

        if not student_identifier:
            for key in (
                "student_id",
                "student_no",
                "university_roll",
            ):
                value = response.get(key)

                if value is not None and str(value).strip():
                    student_identifier = str(
                        value
                    ).strip()
                    break

        # ----------------------------------------------------
        # Determine primary identity field
        # ----------------------------------------------------

        identity_field = None

        for captured in captured_identity_fields:
            field = captured.get("field")

            if not isinstance(field, dict):
                continue

            if (
                field.get("identity_type")
                == "student_id_or_roll_number"
            ):
                identity_field = field
                break

        # ----------------------------------------------------
        # Final normalized submission
        # ----------------------------------------------------

        return {
            "submission_id": response.get(
                "response_id"
            ),
            "student_identifier": student_identifier,
            "student_email": student_email,
            "student_name": student_name,
            "submitted_at": response.get(
                "submitted_at"
            ),
            "answers": assessment_answers,
            "identity_field": identity_field,
            "identity_fields": captured_identity_fields,
        }