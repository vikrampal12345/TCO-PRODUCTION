from __future__ import annotations

from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from backend.core.base_tool import BaseTool
from backend.core.tool_result import ToolResult


class GoogleFormsResponsesTool(BaseTool):
    """
    Deterministic Google Forms response collector.

    Responsibilities:
    - authenticate with Google Forms API
    - fetch submitted responses for a form
    - normalize Google API response objects
    - preserve response ID, timestamps, respondent email (when available),
      and submitted answers

    It does NOT:
    - identify students
    - calculate marks
    - modify the database
    - send emails
    """

    name = "google_forms_responses"

    description = (
        "Fetch and normalize submitted responses from a Google Forms quiz."
    )

    capabilities = (
        "form.responses.list",
        "form.responses.get",
    )

    SCOPES = [
        "https://www.googleapis.com/auth/forms.responses.readonly",
    ]

    DISCOVERY_URL = (
        "https://forms.googleapis.com/"
        "$discovery/rest?version=v1"
    )

    def __init__(self) -> None:
        self.project_root = Path(__file__).resolve().parents[2]

        self.credentials_file = (
            self.project_root / "credentials.json"
        )

        # Keep response-read authorization separate from the existing
        # form-creation token so adding the readonly response scope does
        # not break the currently working Google Forms integration.
        self.token_file = (
            self.project_root / "forms_responses_token.json"
        )

    # =========================================================
    # AUTHENTICATION
    # =========================================================

    def _get_credentials(self) -> Credentials:
        if not self.credentials_file.exists():
            raise FileNotFoundError(
                f"Google OAuth credentials file not found: "
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
                # A malformed/old token is discarded and OAuth will run
                # again below.
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
    # FORMS SERVICE
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
        page_size: int = 100,
        page_token: str | None = None,
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
                    f"Unsupported Google Forms response operation: "
                    f"{operation}"
                ),
            )

        if page_size < 1 or page_size > 500:
            return ToolResult.failure(
                error_code="INVALID_PAGE_SIZE",
                error_message="page_size must be between 1 and 500.",
            )

        try:
            service = self._build_service()

            if operation == "form.responses.get":
                return self._get_one_response(
                    service,
                    form_id=form_id,
                    response_id=page_token or "",
                )

            return self._list_responses(
                service,
                form_id=form_id,
                page_size=page_size,
                page_token=page_token,
            )

        except FileNotFoundError as exc:
            return ToolResult.failure(
                error_code="GOOGLE_FORMS_RESPONSE_AUTH_FAILED",
                error_message=str(exc),
            )

        except Exception as exc:
            return ToolResult.failure(
                error_code="GOOGLE_FORMS_RESPONSE_FAILED",
                error_message=str(exc),
            )

    # =========================================================
    # LIST RESPONSES
    # =========================================================

    def _list_responses(
        self,
        service,
        *,
        form_id: str,
        page_size: int,
        page_token: str | None,
    ) -> ToolResult[dict[str, Any]]:
        request_kwargs = {
            "formId": form_id,
            "pageSize": page_size,
        }

        if page_token:
            request_kwargs["pageToken"] = page_token

        response_page = (
            service.forms()
            .responses()
            .list(**request_kwargs)
            .execute()
        )

        raw_responses = response_page.get(
            "responses",
            [],
        )

        normalized = [
            self.normalize_response(
                form_id=form_id,
                response=response,
            )
            for response in raw_responses
        ]

        return ToolResult.ok(
            data={
                "form_id": form_id,
                "responses": normalized,
                "response_count": len(normalized),
                "next_page_token": response_page.get(
                    "nextPageToken"
                ),
            },
            metadata={
                "operation": "form.responses.list",
                "form_id": form_id,
                "page_size": page_size,
            },
        )

    # =========================================================
    # GET ONE RESPONSE
    # =========================================================

    def _get_one_response(
        self,
        service,
        *,
        form_id: str,
        response_id: str,
    ) -> ToolResult[dict[str, Any]]:
        response_id = str(response_id or "").strip()

        if not response_id:
            return ToolResult.failure(
                error_code="RESPONSE_ID_REQUIRED",
                error_message=(
                    "response_id is required for "
                    "form.responses.get."
                ),
            )

        response = (
            service.forms()
            .responses()
            .get(
                formId=form_id,
                responseId=response_id,
            )
            .execute()
        )

        normalized = self.normalize_response(
            form_id=form_id,
            response=response,
        )

        return ToolResult.ok(
            data=normalized,
            metadata={
                "operation": "form.responses.get",
                "form_id": form_id,
                "response_id": response_id,
            },
        )

    # =========================================================
    # NORMALIZATION
    # =========================================================

    @classmethod
    def normalize_response(
        cls,
        *,
        form_id: str,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convert one Google FormResponse into a stable TCO structure.

        Google Forms answers are keyed by question/item ID.
        Every answer may contain one or more textAnswers.values.
        """

        response_id = str(
            response.get("responseId", "")
        ).strip()

        create_time = str(
            response.get("createTime", "")
        ).strip()

        last_submitted_time = str(
            response.get("lastSubmittedTime", "")
        ).strip()

        respondent_email = str(
            response.get("respondentEmail", "")
        ).strip()

        raw_answers = response.get(
            "answers",
            {},
        ) or {}

        answers: list[dict[str, Any]] = []

        for question_id, answer in raw_answers.items():
            answer = answer or {}

            text_answers = (
                answer.get("textAnswers", {})
                or {}
            )

            values = text_answers.get(
                "answers",
                [],
            ) or []

            normalized_values = []

            for value in values:
                if isinstance(value, dict):
                    normalized_values.append(
                        str(
                            value.get("value", "")
                        )
                    )
                else:
                    normalized_values.append(
                        str(value)
                    )

            grade = answer.get(
                "grade"
            )

            normalized_grade = (
                dict(grade)
                if isinstance(grade, dict)
                else None
            )

            answers.append(
                {
                    "question_id": str(
                        question_id
                    ),
                    "values": normalized_values,
                    "grade": normalized_grade,
                }
            )

        return {
            "form_id": form_id,
            "response_id": response_id,
            "create_time": create_time,
            "submitted_at": last_submitted_time,
            "respondent_email": respondent_email,
            "answers": answers,
            "answer_count": len(answers),
            "raw_response": response,
        }


def fetch_form_responses(
    form_id: str,
    *,
    page_size: int = 100,
    page_token: str | None = None,
) -> ToolResult[dict[str, Any]]:
    """Convenience function for workflows/tests."""

    tool = GoogleFormsResponsesTool()

    return tool.execute(
        operation="form.responses.list",
        form_id=form_id,
        page_size=page_size,
        page_token=page_token,
    )


__all__ = [
    "GoogleFormsResponsesTool",
    "fetch_form_responses",
]
