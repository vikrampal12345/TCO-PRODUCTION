from __future__ import annotations

from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from backend.core.base_tool import BaseTool
from backend.core.tool_result import ToolResult


class GoogleFormsMetadataTool(BaseTool):
    """
    Deterministic Google Forms metadata / answer-key retrieval tool.

    Responsibilities:
    - authenticate with Google Forms API using read-only scope
    - fetch a form definition
    - extract question metadata
    - extract quiz grading / answer-key information
    - normalize the result for downstream Evaluation Agent

    It does NOT:
    - evaluate student submissions
    - identify students
    - modify the database
    - modify the Google Form
    - send emails
    """

    name = "google_forms_metadata"

    # Canonical Google Forms identity question used by TCO.
    IDENTITY_FIELD_TITLE = "Student ID / Roll Number"

    description = (
        "Fetch and normalize Google Forms quiz metadata, questions, "
        "options, marks, and grading answer keys."
    )

    capabilities = (
        "form.metadata.get",
    )

    SCOPES = [
        "https://www.googleapis.com/auth/forms.body.readonly",
    ]

    DISCOVERY_URL = (
        "https://forms.googleapis.com/"
        "$discovery/rest?version=v1"
    )
    IDENTITY_FIELD_DEFINITIONS = {
        "student name": "student_name",
        "student id / roll number": "student_id_or_roll_number",
        "email id": "student_email",
    }

    def __init__(self) -> None:
        self.project_root = Path(__file__).resolve().parents[2]

        self.credentials_file = (
            self.project_root / "credentials.json"
        )

        # Keep form-metadata authorization separate from form creation
        # and response collection tokens.
        self.token_file = (
            self.project_root / "forms_metadata_token.json"
        )

    # =========================================================
    # AUTHENTICATION
    # =========================================================

    def _get_credentials(self) -> Credentials:
        if not self.credentials_file.exists():
            raise FileNotFoundError(
                "Google OAuth credentials file not found: "
                f"{self.credentials_file}"
            )

        creds: Credentials | None = None

        if self.token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(
                    str(self.token_file),
                    self.SCOPES,
                )
            except Exception:
                creds = None

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_file),
                self.SCOPES,
            )

            creds = flow.run_local_server(
                port=0,
                access_type="offline",
                prompt="consent",
            )

            self.token_file.write_text(
                creds.to_json(),
                encoding="utf-8",
            )

        return creds

    # =========================================================
    # GOOGLE FORMS SERVICE
    # =========================================================

    def _build_service(self):
        creds = self._get_credentials()

        return build(
            "forms",
            "v1",
            credentials=creds,
            discoveryServiceUrl=self.DISCOVERY_URL,
            static_discovery=False,
        )

    # =========================================================
    # EXECUTE
    # =========================================================

    def execute(
        self,
        operation: str,
        *,
        form_id: str,
    ) -> ToolResult[dict[str, Any]]:
        form_id = str(form_id or "").strip()

        if not form_id:
            return ToolResult.failure(
                error_code="FORM_ID_REQUIRED",
                error_message="form_id is required.",
            )

        if operation not in self.capabilities:
            return ToolResult.failure(
                error_code="UNSUPPORTED_OPERATION",
                error_message=(
                    "Unsupported Google Forms metadata operation: "
                    f"{operation}"
                ),
            )

        try:
            service = self._build_service()

            response = (
                service.forms()
                .get(formId=form_id)
                .execute()
            )

            normalized = self.normalize_form(
                form_id=form_id,
                form=response,
            )

            return ToolResult.ok(
                data=normalized,
                metadata={
                    "form_id": form_id,
                    "question_count": len(
                        normalized["questions"]
                    ),
                    "is_quiz": normalized["is_quiz"],
                },
            )

        except FileNotFoundError as exc:
            return ToolResult.failure(
                error_code="GOOGLE_FORMS_METADATA_AUTH_FAILED",
                error_message=str(exc),
            )

        except Exception as exc:
            return ToolResult.failure(
                error_code="GOOGLE_FORMS_METADATA_FAILED",
                error_message=str(exc),
            )

    # =========================================================
    # NORMALIZATION
    # =========================================================
    @classmethod
    def normalize_form(
        cls,
        *,
        form_id: str,
        form: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convert the raw Google Forms Form resource into a stable
        TCO contract.

        Identity fields are separated from assessment questions.

        Identity fields:
            - Student Name
            - Student ID / Roll Number
            - Email ID

        Identity fields are excluded from:
            - questions
            - answer_key
            - marking_scheme
        """

        settings = (
            form.get("settings", {})
            or {}
        )

        quiz_settings = (
            settings.get("quizSettings", {})
            or {}
        )

        raw_items = (
            form.get("items", [])
            or []
        )

        questions: list[dict[str, Any]] = []
        identity_fields: list[dict[str, Any]] = []

        for item in raw_items:
            if not isinstance(item, dict):
                continue

            question_item = item.get(
                "questionItem"
            )

            if not isinstance(question_item, dict):
                continue

            question = question_item.get(
                "question",
                {},
            )

            if not isinstance(question, dict):
                continue

            title = cls._normalize_text(
                item.get(
                    "title",
                    "",
                )
            )

            identity_type = (
                cls.IDENTITY_FIELD_DEFINITIONS.get(
                    title
                )
            )

            # -------------------------------------------------
            # Identity field
            # -------------------------------------------------

            if identity_type is not None:
                identity_fields.append(
                    {
                        "item_id": item.get(
                            "itemId"
                        ),
                        "question_id": question.get(
                            "questionId"
                        ),
                        "title": item.get(
                            "title",
                            "",
                        ),
                        "required": bool(
                            question.get(
                                "required",
                                False,
                            )
                        ),
                        "question_type": "text",
                        "identity_type": identity_type,
                        "raw_item": item,
                        "raw_question": question,
                    }
                )

                continue

            # -------------------------------------------------
            # Assessment question
            # -------------------------------------------------

            normalized = cls.normalize_question(
                item=item,
                question=question,
            )

            questions.append(normalized)

        answer_key = [
            cls.question_to_answer_key(question)
            for question in questions
        ]

        marking_scheme = [
            cls.question_to_marking_scheme(question)
            for question in questions
        ]

        # Keep identity fields in the canonical order:
        # Student Name -> Student ID / Roll Number -> Email ID
        identity_order = {
            title: index
            for index, title in enumerate(
                cls.IDENTITY_FIELD_DEFINITIONS.keys()
            )
        }

        identity_fields.sort(
            key=lambda field: identity_order.get(
                cls._normalize_text(
                    field.get(
                        "title",
                        "",
                    )
                ),
                999,
            )
        )

        return {
            "form_id": form_id,
            "title": (
                form.get("info", {})
                .get("title", "")
            ),
            "description": (
                form.get("info", {})
                .get("description", "")
            ),
            "is_quiz": bool(
                quiz_settings.get(
                    "isQuiz",
                    False,
                )
            ),
            "responder_url": (
                form.get("responderUri")
                or ""
            ),
            "revision_id": form.get(
                "revisionId"
            ),
            "question_count": len(
                questions
            ),
            "questions": questions,
            "answer_key": answer_key,
            "marking_scheme": marking_scheme,
            "identity_field_count": len(
                identity_fields
            ),
            "identity_fields": identity_fields,
            "raw_form": form,
        }
    
    @classmethod
    def normalize_question(
        cls,
        *,
        item: dict[str, Any],
        question: dict[str, Any],
    ) -> dict[str, Any]:
        choice = question.get(
            "choiceQuestion"
        )

        text_question = question.get(
            "textQuestion"
        )

        scale_question = question.get(
            "scaleQuestion"
        )

        date_question = question.get(
            "dateQuestion"
        )

        time_question = question.get(
            "timeQuestion"
        )

        # Determine the Google Forms question subtype.
        if isinstance(choice, dict):
            question_type = str(
                choice.get(
                    "type",
                    "choice",
                )
            ).lower()
        elif isinstance(text_question, dict):
            question_type = "text"
        elif isinstance(scale_question, dict):
            question_type = "scale"
        elif isinstance(date_question, dict):
            question_type = "date"
        elif isinstance(time_question, dict):
            question_type = "time"
        else:
            question_type = "unknown"

        grading = (
            question.get("grading", {})
            or {}
        )

        correct_answers = cls._extract_correct_answers(
            grading
        )

        options = []

        if isinstance(choice, dict):
            raw_options = (
                choice.get("options", [])
                or []
            )

            for option in raw_options:
                if not isinstance(option, dict):
                    continue

                options.append(
                    str(
                        option.get(
                            "value",
                            ""
                        )
                    )
                )

        correct_option_indices = (
            cls._find_correct_option_indices(
                options=options,
                correct_answers=correct_answers,
            )
        )

        correct_option = None

        if len(correct_option_indices) == 1:
            correct_option = correct_option_indices[0]

        return {
            "item_id": item.get(
                "itemId"
            ),
            "question_id": question.get(
                "questionId"
            ),
            "question": item.get(
                "title",
                "",
            ),
            "required": bool(
                question.get(
                    "required",
                    False,
                )
            ),
            "question_type": question_type,
            "options": options,
            "points": cls._safe_float(
                grading.get(
                    "pointValue",
                    0,
                )
            ),
            "marks": cls._safe_float(
                grading.get(
                    "pointValue",
                    0,
                )
            ),
            "correct_answers": correct_answers,
            "accepted_answers": correct_answers,
            "correct_option": correct_option,
            "correct_option_indices": (
                correct_option_indices
            ),
            "has_grading": bool(
                grading
            ),
            "grading": grading,
            "raw_item": item,
            "raw_question": question,
        }

    @staticmethod
    def _extract_correct_answers(
        grading: dict[str, Any],
    ) -> list[str]:
        correct_answers = (
            grading.get(
                "correctAnswers",
                {}
            )
            or {}
        )

        raw_answers = (
            correct_answers.get(
                "answers",
                []
            )
            or []
        )

        values: list[str] = []

        for answer in raw_answers:
            if not isinstance(answer, dict):
                continue

            value = answer.get(
                "value"
            )

            if value is not None:
                values.append(
                    str(value)
                )

        return values

    @classmethod
    def _find_correct_option_indices(
        cls,
        *,
        options: list[str],
        correct_answers: list[str],
    ) -> list[int]:
        """
        Return 1-based option positions, because the existing
        Evaluation Agent supports 1-based correct_option values.
        """

        normalized_options = [
            cls._normalize_text(option)
            for option in options
        ]

        indices: list[int] = []

        for correct_answer in correct_answers:
            normalized_answer = cls._normalize_text(
                correct_answer
            )

            for index, option in enumerate(
                normalized_options,
                start=1,
            ):
                if option == normalized_answer:
                    indices.append(index)
                    break

        return indices

    @classmethod
    def question_to_answer_key(
        cls,
        question: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "question_id": question.get(
                "question_id"
            ),
            "correct_answers": question.get(
                "correct_answers",
                [],
            ),
            "accepted_answers": question.get(
                "accepted_answers",
                [],
            ),
            "correct_option": question.get(
                "correct_option"
            ),
            "correct_option_indices": question.get(
                "correct_option_indices",
                [],
            ),
            "points": question.get(
                "points",
                0,
            ),
            "marks": question.get(
                "marks",
                0,
            ),
        }

    @staticmethod
    def question_to_marking_scheme(
        question: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "question_id": question.get(
                "question_id"
            ),
            "max_marks": question.get(
                "marks",
                0,
            ),
            "points": question.get(
                "points",
                0,
            ),
        }

    @staticmethod
    def _safe_float(
        value: Any,
    ) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _normalize_text(
        value: Any,
    ) -> str:
        return " ".join(
            str(value)
            .strip()
            .lower()
            .split()
        )


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================


def fetch_form_metadata(
    form_id: str,
) -> ToolResult[dict[str, Any]]:
    """Convenience wrapper for workflows/tests."""

    tool = GoogleFormsMetadataTool()

    return tool.execute(
        operation="form.metadata.get",
        form_id=form_id,
    )


__all__ = [
    "GoogleFormsMetadataTool",
    "fetch_form_metadata",
]
