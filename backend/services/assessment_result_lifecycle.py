from __future__ import annotations

from typing import Any


class AssessmentResultLifecycleError(RuntimeError):
    """Raised when the assessment result lifecycle cannot continue."""


class AssessmentResultLifecycleService:
    """
    Orchestrates the complete finalized-result lifecycle.

    Flow:

        EvaluationCycleService
                ↓
        AssessmentResultService
                ↓
            ResultStore
                ↓
        ResultEmailService
                ↓
              Gmail

    Responsibilities:
        - run evaluation + result persistence
        - send result email after successful persistence
        - keep result saving independent from email delivery

    This service does NOT:
        - evaluate answers
        - resolve students directly
        - write SQLite directly
        - generate assessments
        - perform OCR
        - perform LLM reasoning
    """

    def __init__(
        self,
        *,
        evaluation_cycle,
        result_email_service,
    ) -> None:
        self.evaluation_cycle = (
            evaluation_cycle
        )

        self.result_email_service = (
            result_email_service
        )

    # ========================================================
    # PUBLIC: PROCESS ALL FORM RESPONSES
    # ========================================================

    def process_form(
        self,
        *,
        form_id: str,
        assessment_id: int,
        school_id: str | None = None,
        class_level: str | None = None,
        section: str | None = None,
        attempt_number: int = 1,
        page_size: int = 100,
        send_email: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Evaluate all responses, save results, and optionally
        send result emails.
        """

        form_id = str(
            form_id or ""
        ).strip()

        if not form_id:
            raise AssessmentResultLifecycleError(
                "form_id is required."
            )

        if assessment_id <= 0:
            raise AssessmentResultLifecycleError(
                "assessment_id must be greater than 0."
            )

        lifecycle_results = (
            self.evaluation_cycle.evaluate_and_save_form(
                form_id=form_id,
                assessment_id=assessment_id,
                school_id=school_id,
                class_level=class_level,
                section=section,
                attempt_number=attempt_number,
                page_size=page_size,
            )
        )

        return [
            self._process_saved_result(
                lifecycle_result=lifecycle_result,
                send_email=send_email,
            )
            for lifecycle_result
            in lifecycle_results
        ]

    # ========================================================
    # PUBLIC: PROCESS ONE RESPONSE
    # ========================================================

    def process_response(
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
        send_email: bool = True,
    ) -> dict[str, Any]:
        """
        Evaluate one response, save its result, and optionally
        send the result email.
        """

        form_id = str(
            form_id or ""
        ).strip()

        response_id = str(
            response_id or ""
        ).strip()

        if not form_id:
            raise AssessmentResultLifecycleError(
                "form_id is required."
            )

        if not response_id:
            raise AssessmentResultLifecycleError(
                "response_id is required."
            )

        if assessment_id <= 0:
            raise AssessmentResultLifecycleError(
                "assessment_id must be greater than 0."
            )

        lifecycle_result = (
            self.evaluation_cycle.evaluate_and_save_response(
                form_id=form_id,
                response_id=response_id,
                assessment_id=assessment_id,
                school_id=school_id,
                class_level=class_level,
                section=section,
                attempt_number=attempt_number,
                page_size=page_size,
            )
        )

        return self._process_saved_result(
            lifecycle_result=lifecycle_result,
            send_email=send_email,
        )

    # ========================================================
    # PROCESS SAVED RESULT
    # ========================================================

    def _process_saved_result(
        self,
        *,
        lifecycle_result: dict[str, Any],
        send_email: bool,
    ) -> dict[str, Any]:
        """
        Process one EvaluationCycle lifecycle result.

        Important:
        A result is already persisted before email delivery starts.

        Therefore an email failure does NOT mean that the result
        itself failed to save.
        """

        status = lifecycle_result.get(
            "status"
        )

        # ----------------------------------------------------
        # Review required
        # ----------------------------------------------------

        if status == "review_required":
            return {
                **lifecycle_result,
                "email": {
                    "status": "not_sent",
                    "reason": "review_required",
                },
                "lifecycle_status": (
                    "review_required"
                ),
            }

        # ----------------------------------------------------
        # Result was not saved
        # ----------------------------------------------------

        if status != "saved":
            return {
                **lifecycle_result,
                "email": {
                    "status": "not_sent",
                    "reason": (
                        "result_not_saved"
                    ),
                },
                "lifecycle_status": (
                    "result_not_saved"
                ),
            }

        # ----------------------------------------------------
        # Extract saved result
        # ----------------------------------------------------

        saved_result = lifecycle_result.get(
            "saved_result"
        )

        if not saved_result:
            raise AssessmentResultLifecycleError(
                "Evaluation lifecycle returned "
                "status='saved' but no saved_result."
            )

        result_id = saved_result.get(
            "result_id"
        )

        if result_id is None:
            raise AssessmentResultLifecycleError(
                "Saved result does not contain result_id."
            )

        result_id = int(result_id)

        # ----------------------------------------------------
        # Email disabled
        # ----------------------------------------------------

        if not send_email:
            return {
                **lifecycle_result,
                "email": {
                    "status": "not_sent",
                    "reason": "email_disabled",
                    "result_id": result_id,
                },
                "lifecycle_status": (
                    "result_saved_email_not_sent"
                ),
            }

        # ----------------------------------------------------
        # Send result email
        # ----------------------------------------------------

        email_result = (
            self.result_email_service.send_result(
                result_id=result_id,
            )
        )

        email_status = email_result.get(
            "status"
        )

        # ----------------------------------------------------
        # Email successful
        # ----------------------------------------------------

        if email_status == "sent":
            return {
                **lifecycle_result,
                "email": email_result,
                "lifecycle_status": (
                    "result_saved_email_sent"
                ),
            }

        # ----------------------------------------------------
        # Already sent
        # ----------------------------------------------------

        if email_status == "already_sent":
            return {
                **lifecycle_result,
                "email": email_result,
                "lifecycle_status": (
                    "result_saved_email_already_sent"
                ),
            }

        # ----------------------------------------------------
        # Email failed / skipped
        # ----------------------------------------------------

        return {
            **lifecycle_result,
            "email": email_result,
            "lifecycle_status": (
                "result_saved_email_failed"
                if email_status == "failed"
                else "result_saved_email_skipped"
            ),
        }


__all__ = [
    "AssessmentResultLifecycleError",
    "AssessmentResultLifecycleService",
]