from __future__ import annotations

from typing import Any


class ResultEmailServiceError(Exception):
    """Raised when result email processing fails."""


class ResultEmailService:
    """
    Sends evaluated assessment results to students.

    Responsibilities:
    - Load saved result from ResultStore.
    - Validate student email.
    - Build result email.
    - Send email through GmailTool.
    - Update result email status in ResultStore.

    This service does NOT:
    - evaluate answers
    - resolve student identity
    - generate assessments
    - perform LLM reasoning
    """

    def __init__(
        self,
        *,
        result_store,
        gmail_tool,
    ) -> None:
        self.result_store = result_store
        self.gmail_tool = gmail_tool

    # =========================================================
    # PUBLIC API
    # =========================================================

    def send_result(
        self,
        *,
        result_id: int,
        subject: str | None = None,
        body: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """
        Send one saved assessment result to the student.

        Returns a normalized lifecycle result.
        """

        if result_id <= 0:
            raise ResultEmailServiceError(
                "result_id must be greater than 0."
            )

        result = self.result_store.get_result(
            result_id=result_id
        )

        if result is None:
            raise ResultEmailServiceError(
                f"Result not found: result_id={result_id}"
            )

        current_email_status = (
            result.get("result_email_status")
            or "not_sent"
        )

        # -----------------------------------------------------
        # Prevent accidental duplicate emails.
        # -----------------------------------------------------

        if (
            current_email_status == "sent"
            and not force
        ):
            return {
                "status": "already_sent",
                "result_id": result_id,
                "recipient": result.get(
                    "student_email"
                ),
                "result": result,
            }

        # -----------------------------------------------------
        # Student email.
        # -----------------------------------------------------

        student_email = (
            result.get("student_email")
            or ""
        ).strip()

        if not student_email:
            updated = (
                self.result_store.update_result_email_status(
                    result_id=result_id,
                    status="skipped",
                    error="Student email address is missing.",
                )
            )

            return {
                "status": "skipped",
                "result_id": result_id,
                "recipient": None,
                "error": "Student email address is missing.",
                "result": updated,
            }

        # -----------------------------------------------------
        # Build subject/body if not explicitly supplied.
        # -----------------------------------------------------

        email_subject = (
            subject
            or self._build_subject(result)
        )

        email_body = (
            body
            or self._build_body(result)
        )

        # -----------------------------------------------------
        # Send through existing Gmail tool.
        #
        # Existing TCO Gmail interface:
        #
        # operation="email.send_bulk"
        # recipients=[email]
        # subject=...
        # body=...
        # -----------------------------------------------------

        send_result = self.gmail_tool.execute(
            operation="email.send_bulk",
            recipients=[student_email],
            subject=email_subject,
            body=email_body,
        )

        if not send_result.success:
            error_message = (
                send_result.error_message
                or "Could not send result email."
            )

            updated = (
                self.result_store.update_result_email_status(
                    result_id=result_id,
                    status="failed",
                    error=error_message,
                )
            )

            return {
                "status": "failed",
                "result_id": result_id,
                "recipient": student_email,
                "subject": email_subject,
                "error": error_message,
                "result": updated,
            }

        send_data = (
            send_result.data
            or {}
        )

        # -----------------------------------------------------
        # Mark result email as successfully sent.
        # -----------------------------------------------------

        updated = (
            self.result_store.update_result_email_status(
                result_id=result_id,
                status="sent",
            )
        )

        return {
            "status": "sent",
            "result_id": result_id,
            "recipient": student_email,
            "subject": email_subject,
            "send_data": send_data,
            "result": updated,
        }

    # =========================================================
    # EMAIL CONTENT
    # =========================================================

    @staticmethod
    def _build_subject(
        result: dict[str, Any],
    ) -> str:
        assessment_title = (
            result.get("assessment_title")
            or result.get("topic")
            or "Assessment"
        )

        return (
            f"TCO Assessment Result - "
            f"{assessment_title}"
        )

    @staticmethod
    def _build_body(
        result: dict[str, Any],
    ) -> str:
        student_name = (
            result.get("student_name")
            or "Student"
        )

        assessment_title = (
            result.get("assessment_title")
            or "Assessment"
        )

        subject = (
            result.get("subject")
            or ""
        )

        topic = (
            result.get("topic")
            or ""
        )

        obtained_marks = (
            result.get("obtained_marks")
            or 0
        )

        total_marks = (
            result.get("total_marks")
            or 0
        )

        percentage = (
            result.get("percentage")
            or 0
        )

        correct_answers = (
            result.get("correct_answers")
            or 0
        )

        wrong_answers = (
            result.get("wrong_answers")
            or 0
        )

        unanswered = (
            result.get("unanswered")
            or 0
        )

        return f"""Hello {student_name},

Your assessment result has been evaluated.

Assessment: {assessment_title}
Subject: {subject}
Topic: {topic}

Result:
Marks: {obtained_marks} / {total_marks}
Percentage: {percentage}%

Correct Answers: {correct_answers}
Wrong Answers: {wrong_answers}
Unanswered: {unanswered}

Please contact your teacher if you have any questions regarding your result.

Regards,
TCO - Teacher Co-Worker
"""

    # =========================================================
    # BULK PENDING RESULT EMAILS
    # =========================================================

    def send_pending_results(
        self,
        *,
        assessment_id: int | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        Send all pending result emails returned by ResultStore.
        """

        pending_results = (
            self.result_store.get_pending_result_emails(
                assessment_id=assessment_id,
                limit=limit,
            )
        )

        results: list[dict[str, Any]] = []

        sent_count = 0
        failed_count = 0
        skipped_count = 0

        for result in pending_results:
            result_id = int(
                result["result_id"]
            )

            outcome = self.send_result(
                result_id=result_id
            )

            results.append(outcome)

            status = outcome.get("status")

            if status == "sent":
                sent_count += 1
            elif status == "failed":
                failed_count += 1
            elif status == "skipped":
                skipped_count += 1

        return {
            "status": "completed",
            "total": len(pending_results),
            "sent": sent_count,
            "failed": failed_count,
            "skipped": skipped_count,
            "results": results,
        }


__all__ = [
    "ResultEmailService",
    "ResultEmailServiceError",
]