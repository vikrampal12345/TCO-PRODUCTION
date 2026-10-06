from __future__ import annotations

from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from backend.core.base_tool import BaseTool
from backend.core.tool_result import ToolResult


class GoogleFormsTool(BaseTool):
    """
    Deterministic Google Forms tool.

    Responsibilities:
    - Authenticate with Google
    - Create a Google Form
    - Convert it to a quiz
    - Add MCQ questions
    - Configure answer keys and marks
    - Publish the form when requested
    - Return the responder URL

    It does NOT:
    - generate questions
    - review questions
    - make business decisions
    """

    name = "google_forms"

    description = (
        "Creates and publishes a Google Forms quiz from supplied MCQ "
        "questions and returns the responder URL."
    )

    capabilities = (
        "form.create_quiz",
    )

    SCOPES = [
        "https://www.googleapis.com/auth/forms.body",
    ]

    def __init__(self) -> None:
        self.project_root = Path(__file__).resolve().parents[2]

        self.credentials_file = (
            self.project_root / "credentials.json"
        )

        self.token_file = (
            self.project_root / "forms_token.json"
        )

    # =========================================================
    # AUTHENTICATION
    # =========================================================

    def _get_credentials(self) -> Credentials:
        creds: Credentials | None = None

        # -----------------------------------------------------
        # Reuse saved token
        # -----------------------------------------------------

        if self.token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(
                    str(self.token_file),
                    self.SCOPES,
                )
            except Exception:
                creds = None

        # -----------------------------------------------------
        # Existing valid credentials
        # -----------------------------------------------------

        if creds and creds.valid:
            return creds

        # -----------------------------------------------------
        # Refresh expired credentials
        # -----------------------------------------------------

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        # -----------------------------------------------------
        # New OAuth flow
        # -----------------------------------------------------

        else:
            if not self.credentials_file.exists():
                raise FileNotFoundError(
                    "Google OAuth credentials file not found: "
                    f"{self.credentials_file}"
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_file),
                self.SCOPES,
            )

            creds = flow.run_local_server(
                port=0,
                access_type="offline",
                prompt="consent",
            )

        # -----------------------------------------------------
        # Save token
        # -----------------------------------------------------

        self.token_file.write_text(
            creds.to_json(),
            encoding="utf-8",
        )

        return creds

    # =========================================================
    # BUILD GOOGLE FORMS SERVICE
    # =========================================================

    def _build_service(self):
        creds = self._get_credentials()

        return build(
            "forms",
            "v1",
            credentials=creds,
            discoveryServiceUrl=(
                "https://forms.googleapis.com/"
                "$discovery/rest?version=v1"
            ),
            static_discovery=False,
        )

    # =========================================================
    # VALIDATE QUESTIONS
    # =========================================================

    def _validate_questions(
        self,
        questions: Any,
    ) -> None:

        if not isinstance(questions, list):
            raise ValueError(
                "questions must be a list."
            )

        if not questions:
            raise ValueError(
                "At least one question is required."
            )

        for index, question in enumerate(
            questions,
            start=1,
        ):

            if not isinstance(question, dict):
                raise ValueError(
                    f"Question {index} must be a dictionary."
                )

            question_text = str(
                question.get("question", "")
            ).strip()

            options = question.get("options")

            correct_option = question.get(
                "correct_option"
            )

            if not question_text:
                raise ValueError(
                    f"Question {index} is missing question text."
                )

            if not isinstance(options, list):
                raise ValueError(
                    f"Question {index} options must be a list."
                )

            if len(options) != 4:
                raise ValueError(
                    f"Question {index} must have exactly 4 options."
                )

            for option in options:
                if not isinstance(option, str):
                    raise ValueError(
                        f"Question {index} contains a non-string option."
                    )

                if not option.strip():
                    raise ValueError(
                        f"Question {index} contains an empty option."
                    )

            if not isinstance(correct_option, int):
                raise ValueError(
                    f"Question {index} correct_option "
                    "must be an integer."
                )

            if not (
                1 <= correct_option <= len(options)
            ):
                raise ValueError(
                    f"Question {index} correct_option must be "
                    f"between 1 and {len(options)}."
                )

            marks = question.get("marks", 1)

            if not isinstance(marks, int):
                raise ValueError(
                    f"Question {index} marks must be an integer."
                )

            if marks < 1:
                raise ValueError(
                    f"Question {index} marks must be >= 1."
                )

    # =========================================================
    # CREATE QUIZ
    # =========================================================

    def execute(
        self,
        *,
        title: str,
        questions: list[dict[str, Any]],
        description: str = "",
        publish: bool = True,
        **kwargs: Any,
    ) -> ToolResult:

        try:
            # -------------------------------------------------
            # Basic title validation
            # -------------------------------------------------

            title = str(title).strip()

            if not title:
                return ToolResult.failure(
                    "INVALID_TITLE",
                    "Google Form title cannot be empty.",
                )

            # -------------------------------------------------
            # Validate questions
            # -------------------------------------------------

            self._validate_questions(
                questions
            )

            # -------------------------------------------------
            # Build API client
            # -------------------------------------------------

            form_service = self._build_service()

            # =================================================
            # STEP 1: CREATE BLANK FORM
            # =================================================
            #
            # IMPORTANT:
            # Google Forms currently allows only info.title
            # in forms.create().
            #
            # Description is added later through batchUpdate.
            # =================================================

            create_body = {
                "info": {
                    "title": title,
                }
            }

            created_form = (
                form_service.forms()
                .create(
                    body=create_body
                )
                .execute()
            )

            form_id = created_form.get(
                "formId"
            )

            if not form_id:
                return ToolResult.failure(
                    "FORM_ID_MISSING",
                    "Google Forms API did not return a formId.",
                )

            # =================================================
            # STEP 2: BATCH UPDATE
            # =================================================

            requests: list[dict[str, Any]] = []

            # -------------------------------------------------
            # 2A. Add description
            # -------------------------------------------------

            if description.strip():

                requests.append(
                    {
                        "updateFormInfo": {
                            "info": {
                                "description": (
                                    description.strip()
                                )
                            },
                            "updateMask": "description",
                        }
                    }
                )

            # -------------------------------------------------
            # 2B. Convert to quiz
            # -------------------------------------------------

            requests.append(
                {
                    "updateSettings": {
                        "settings": {
                            "quizSettings": {
                                "isQuiz": True,
                            }
                        },
                        "updateMask": (
                            "quizSettings.isQuiz"
                        ),
                    }
                }
            )

            # =================================================
            # STEP 3: ADD QUESTIONS
            # =================================================

            for index, question in enumerate(
                questions
            ):

                question_text = str(
                    question["question"]
                ).strip()

                options = [
                    str(option).strip()
                    for option in question["options"]
                ]

                correct_option = int(
                    question["correct_option"]
                )

                marks = int(
                    question.get(
                        "marks",
                        1,
                    )
                )

                correct_answer_text = options[
                    correct_option - 1
                ]

                requests.append(
                    {
                        "createItem": {
                            "item": {
                                "title": question_text,
                                "questionItem": {
                                    "question": {
                                        "required": True,
                                        "choiceQuestion": {
                                            "type": "RADIO",
                                            "options": [
                                                {
                                                    "value": option
                                                }
                                                for option in options
                                            ],
                                            "shuffle": False,
                                        },
                                        "grading": {
                                            "pointValue": marks,
                                            "correctAnswers": {
                                                "answers": [
                                                    {
                                                        "value": (
                                                            correct_answer_text
                                                        )
                                                    }
                                                ]
                                            },
                                        },
                                    }
                                },
                            },
                            "location": {
                                "index": index,
                            },
                        }
                    }
                )

            # =================================================
            # STEP 4: APPLY ALL FORM CHANGES
            # =================================================

            form_service.forms().batchUpdate(
                formId=form_id,
                body={
                    "requests": requests,
                },
            ).execute()

            # =================================================
            # STEP 5: PUBLISH
            # =================================================

            if publish:

                publish_body = {
                    "publishSettings": {
                        "publishState": {
                            "isPublished": True,
                            "isAcceptingResponses": True,
                        }
                    },
                    "updateMask": "publishState",
                }

                form_service.forms().setPublishSettings(
                    formId=form_id,
                    body=publish_body,
                ).execute()

            # =================================================
            # STEP 6: GET FINAL FORM
            # =================================================

            final_form = (
                form_service.forms()
                .get(
                    formId=form_id
                )
                .execute()
            )

            # -------------------------------------------------
            # Responder URL
            # -------------------------------------------------

            responder_url = final_form.get(
                "responderUri"
            )

            # -------------------------------------------------
            # Editor URL
            # -------------------------------------------------

            edit_url = (
                "https://docs.google.com/forms/d/"
                f"{form_id}/edit"
            )

            # -------------------------------------------------
            # Publish state
            # -------------------------------------------------

            publish_settings = (
                final_form.get(
                    "publishSettings",
                    {}
                )
            )

            publish_state = (
                publish_settings.get(
                    "publishState",
                    {}
                )
            )

            is_published = bool(
                publish_state.get(
                    "isPublished",
                    False,
                )
            )

            is_accepting_responses = bool(
                publish_state.get(
                    "isAcceptingResponses",
                    False,
                )
            )

            # =================================================
            # SUCCESS
            # =================================================

            return ToolResult.ok(
                data={
                    "form_id": form_id,
                    "title": (
                        final_form
                        .get("info", {})
                        .get("title", title)
                    ),
                    "responder_url": responder_url,
                    "edit_url": edit_url,
                    "is_published": is_published,
                    "is_accepting_responses": (
                        is_accepting_responses
                    ),
                    "question_count": len(
                        questions
                    ),
                },
                metadata={
                    "tool": self.name,
                    "published": is_published,
                },
            )

        # =====================================================
        # ERROR HANDLING
        # =====================================================

        except FileNotFoundError as exc:

            return ToolResult.failure(
                "GOOGLE_FORMS_AUTH_FAILED",
                str(exc),
            )

        except HttpError as exc:

            return ToolResult.failure(
                "GOOGLE_FORM_CREATE_FAILED",
                str(exc),
            )

        except ValueError as exc:

            return ToolResult.failure(
                "INVALID_FORM_DATA",
                str(exc),
            )

        except Exception as exc:

            return ToolResult.failure(
                "GOOGLE_FORM_CREATE_FAILED",
                str(exc),
            )
