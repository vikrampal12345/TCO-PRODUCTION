from __future__ import annotations

from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from backend.core.base_tool import BaseTool
from backend.core.tool_result import ToolResult


# =========================================================
# TCO GOOGLE FORM IDENTITY FIELD CONSTANTS
# =========================================================

IDENTITY_FIELD_TITLE = "Student ID / Roll Number"
STUDENT_NAME_FIELD_TITLE = "Student Name"
EMAIL_FIELD_TITLE = "Email ID"


class GoogleFormsIdentityTool(BaseTool):
    """
    Deterministic Google Forms identity-field tool.

    Purpose:
        Ensure every TCO assessment form contains the required
        student identity fields:

            1. Student Name
            2. Student ID / Roll Number
            3. Email ID

    Responsibilities:
        - Authenticate with Google Forms API
        - Inspect a Google Form
        - Detect existing identity fields
        - Add missing identity fields
        - Keep the operation idempotent

    It does NOT:
        - identify a student in the database
        - evaluate answers
        - calculate marks
        - send emails
        - generate questions
    """

    name = "google_forms_identity"

    description = (
        "Adds and maintains the required Student Name, "
        "Student ID / Roll Number, and Email ID fields "
        "in a Google Form."
    )

    capabilities = (
        "form.identity.add",
    )

    SCOPES = [
        "https://www.googleapis.com/auth/forms.body",
    ]

    DISCOVERY_URL = (
        "https://forms.googleapis.com/"
        "$discovery/rest?version=v1"
    )

    # Keep these as class attributes too so existing code that
    # references GoogleFormsIdentityTool.IDENTITY_FIELD_TITLE
    # continues to work.
    IDENTITY_FIELD_TITLE = (
        IDENTITY_FIELD_TITLE
    )

    STUDENT_NAME_FIELD_TITLE = (
        STUDENT_NAME_FIELD_TITLE
    )

    EMAIL_FIELD_TITLE = (
        EMAIL_FIELD_TITLE
    )

    # Desired order inside a TCO form.
    IDENTITY_FIELD_DEFINITIONS = (
        (
            STUDENT_NAME_FIELD_TITLE,
            "student_name",
        ),
        (
            IDENTITY_FIELD_TITLE,
            "student_id_or_roll_number",
        ),
        (
            EMAIL_FIELD_TITLE,
            "student_email",
        ),
    )

    def __init__(self) -> None:
        self.project_root = (
            Path(__file__).resolve().parents[2]
        )

        self.credentials_file = (
            self.project_root
            / "credentials.json"
        )

        # Google Forms creation and identity
        # modification use the same Forms body scope/token.
        self.token_file = (
            self.project_root
            / "token.json"
        )

    # =========================================================
    # AUTHENTICATION
    # =========================================================

    def _get_credentials(
        self,
    ) -> Credentials:
        if not self.credentials_file.exists():
            raise FileNotFoundError(
                "Google OAuth credentials file not found: "
                f"{self.credentials_file}"
            )

        creds: Credentials | None = None

        # -----------------------------------------------------
        # Existing token
        # -----------------------------------------------------

        if self.token_file.exists():
            try:
                creds = (
                    Credentials
                    .from_authorized_user_file(
                        str(self.token_file),
                        self.SCOPES,
                    )
                )
            except Exception:
                creds = None

        # -----------------------------------------------------
        # Refresh expired token
        # -----------------------------------------------------

        if (
            creds
            and creds.expired
            and creds.refresh_token
        ):
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        # -----------------------------------------------------
        # New OAuth flow
        # -----------------------------------------------------

        if not creds or not creds.valid:
            flow = (
                InstalledAppFlow
                .from_client_secrets_file(
                    str(
                        self.credentials_file
                    ),
                    self.SCOPES,
                )
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
            discoveryServiceUrl=(
                self.DISCOVERY_URL
            ),
            static_discovery=False,
        )

    # =========================================================
    # IDENTITY ITEM
    # =========================================================

    @classmethod
    def build_identity_item(
        cls,
        *,
        title: str | None = None,
        required: bool = True,
    ) -> dict[str, Any]:
        """
        Build one TCO identity field.

        Backward compatibility:
            If title is omitted, the historical
            Student ID / Roll Number field is created.
        """

        title = (
            cls.IDENTITY_FIELD_TITLE
            if title is None
            else str(title).strip()
        )

        if not title:
            raise ValueError(
                "Identity field title cannot be empty."
            )

        return {
            "title": title,
            "questionItem": {
                "question": {
                    "required": required,
                    "textQuestion": {
                        "paragraph": False,
                    },
                },
            },
        }

    # =========================================================
    # CREATE ITEM REQUEST
    # =========================================================

    @classmethod
    def build_create_request(
        cls,
        *,
        title: str | None = None,
        index: int = 0,
        required: bool = True,
    ) -> dict[str, Any]:
        """
        Build a Google Forms batchUpdate createItem request.

        Backward compatibility:
            If title is omitted, the historical
            Student ID / Roll Number field is created.
        """

        return {
            "createItem": {
                "item": (
                    cls.build_identity_item(
                        title=title,
                        required=required,
                    )
                ),
                "location": {
                    "index": index,
                },
            }
        }

    # =========================================================
    # FIND EXISTING IDENTITY FIELDS
    # =========================================================

    @classmethod
    def find_identity_fields(
        cls,
        form: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Find all supported TCO identity fields.

        Supported fields:
            - Student Name
            - Student ID / Roll Number
            - Email ID

        Returns the identity-field contract used by
        downstream metadata/evaluation services.
        """

        identity_fields: list[
            dict[str, Any]
        ] = []

        field_definitions = dict(
            cls.IDENTITY_FIELD_DEFINITIONS
        )

        raw_items = (
            form.get(
                "items",
                [],
            )
            or []
        )

        for item in raw_items:
            if not isinstance(
                item,
                dict,
            ):
                continue

            title = str(
                item.get(
                    "title",
                    "",
                )
                or ""
            ).strip()

            identity_type = (
                field_definitions.get(
                    title
                )
            )

            if identity_type is None:
                continue

            question_item = item.get(
                "questionItem",
                {},
            )

            if not isinstance(
                question_item,
                dict,
            ):
                continue

            question = question_item.get(
                "question",
                {},
            )

            if not isinstance(
                question,
                dict,
            ):
                continue

            question_id = question.get(
                "questionId"
            )

            item_id = item.get(
                "itemId"
            )

            field = {
                "item_id": item_id,
                "question_id": question_id,
                "title": title,
                "required": bool(
                    question.get(
                        "required",
                        False,
                    )
                ),
                "question_type": "text",
                "identity_type": (
                    identity_type
                ),
                "raw_item": item,
                "raw_question": question,
            }

            identity_fields.append(
                field
            )

        # Return identity fields in the
        # canonical TCO order.
        order = {
            title: index
            for index, (
                title,
                _,
            ) in enumerate(
                cls.IDENTITY_FIELD_DEFINITIONS
            )
        }

        identity_fields.sort(
            key=lambda field: order.get(
                field.get("title"),
                999,
            )
        )

        return identity_fields

    # =========================================================
    # ADD ALL REQUIRED IDENTITY FIELDS
    # =========================================================

    def add_student_identity_field(
        self,
        form_id: str,
        *,
        required: bool = True,
    ) -> ToolResult[dict[str, Any]]:
        """
        Ensure all three TCO identity fields exist:

            Student Name
            Student ID / Roll Number
            Email ID

        This method is intentionally kept under the existing
        add_student_identity_field name for backward compatibility.

        If some fields already exist, only missing fields are added.
        Therefore the operation is idempotent.
        """

        form_id = str(
            form_id or ""
        ).strip()

        if not form_id:
            return ToolResult.failure(
                error_code="FORM_ID_REQUIRED",
                error_message=(
                    "form_id is required."
                ),
            )

        try:
            service = self._build_service()

            # -------------------------------------------------
            # Read current form
            # -------------------------------------------------

            form = (
                service.forms()
                .get(
                    formId=form_id
                )
                .execute()
            )

            existing_fields = (
                self.find_identity_fields(
                    form
                )
            )

            existing_by_title = {
                field.get("title"): field
                for field in existing_fields
            }

            added_fields: list[
                dict[str, Any]
            ] = []

            batch_update_responses: list[
                dict[str, Any]
            ] = []

            # -------------------------------------------------
            # Ensure fields in canonical order
            #
            # Desired order:
            #
            #   0 -> Student Name
            #   1 -> Student ID / Roll Number
            #   2 -> Email ID
            #
            # We insert missing fields one by one.
            # -------------------------------------------------

            for desired_index, (
                title,
                identity_type,
            ) in enumerate(
                self.IDENTITY_FIELD_DEFINITIONS
            ):
                if title in existing_by_title:
                    continue

                request = (
                    self.build_create_request(
                        title=title,
                        index=desired_index,
                        required=required,
                    )
                )

                response = (
                    service.forms()
                    .batchUpdate(
                        formId=form_id,
                        body={
                            "requests": [
                                request
                            ]
                        },
                    )
                    .execute()
                )

                batch_update_responses.append(
                    response
                )

                # -------------------------------------------------
                # Fetch the form again after each creation.
                #
                # This keeps indexes deterministic even when
                # some identity fields already existed.
                # -------------------------------------------------

                current_form = (
                    service.forms()
                    .get(
                        formId=form_id
                    )
                    .execute()
                )

                current_fields = (
                    self.find_identity_fields(
                        current_form
                    )
                )

                current_by_title = {
                    field.get("title"): field
                    for field in current_fields
                }

                created_field = (
                    current_by_title.get(
                        title
                    )
                )

                if created_field:
                    added_fields.append(
                        created_field
                    )
                    existing_by_title[
                        title
                    ] = created_field
                else:
                    # API reported success but the expected
                    # field could not be detected afterward.
                    raise RuntimeError(
                        "Google Form field creation "
                        f"succeeded for '{title}', "
                        "but the field could not be "
                        "detected afterward."
                    )

            # -------------------------------------------------
            # Final verification
            # -------------------------------------------------

            updated_form = (
                service.forms()
                .get(
                    formId=form_id
                )
                .execute()
            )

            updated_fields = (
                self.find_identity_fields(
                    updated_form
                )
            )

            updated_by_title = {
                field.get("title"): field
                for field in updated_fields
            }

            missing_titles = [
                title
                for title, _ in (
                    self.IDENTITY_FIELD_DEFINITIONS
                )
                if title
                not in updated_by_title
            ]

            if missing_titles:
                raise RuntimeError(
                    "TCO identity field verification failed. "
                    "Missing fields: "
                    + ", ".join(
                        missing_titles
                    )
                )

            # -------------------------------------------------
            # Canonical primary identity field
            #
            # Keep backward compatibility with existing callers
            # that expect data["identity_field"].
            # -------------------------------------------------

            identity_field = (
                updated_by_title.get(
                    self.IDENTITY_FIELD_TITLE
                )
            )

            identity_fields = [
                updated_by_title[title]
                for title, _ in (
                    self.IDENTITY_FIELD_DEFINITIONS
                )
            ]

            all_already_existed = (
                len(added_fields) == 0
            )

            return ToolResult.ok(
                data={
                    "form_id": form_id,

                    # Backward-compatible primary field.
                    "identity_field": (
                        identity_field
                    ),

                    # New canonical list.
                    "identity_fields": (
                        identity_fields
                    ),

                    "identity_field_count": (
                        len(identity_fields)
                    ),

                    "identity_fields_added": (
                        added_fields
                    ),

                    "identity_fields_added_count": (
                        len(added_fields)
                    ),

                    # Keep old boolean key.
                    "identity_field_added": (
                        not all_already_existed
                    ),

                    "already_exists": (
                        all_already_existed
                    ),

                    "batch_update_responses": (
                        batch_update_responses
                    ),
                },
                metadata={
                    "operation": (
                        "form.identity.add"
                    ),
                    "idempotent": True,
                    "identity_field_count": (
                        len(identity_fields)
                    ),
                },
            )

        except FileNotFoundError as exc:
            return ToolResult.failure(
                error_code=(
                    "GOOGLE_FORMS_AUTH_FAILED"
                ),
                error_message=str(exc),
            )

        except Exception as exc:
            return ToolResult.failure(
                error_code=(
                    "IDENTITY_FIELDS_ADD_FAILED"
                ),
                error_message=str(exc),
            )

    # =========================================================
    # TOOL EXECUTE
    # =========================================================

    def execute(
        self,
        operation: str,
        *,
        form_id: str,
        required: bool = True,
    ) -> ToolResult[dict[str, Any]]:
        """
        BaseTool entry point.
        """

        if operation not in self.capabilities:
            return ToolResult.failure(
                error_code=(
                    "UNSUPPORTED_OPERATION"
                ),
                error_message=(
                    "Unsupported Google Forms identity "
                    f"operation: {operation}"
                ),
            )

        return self.add_student_identity_field(
            form_id=form_id,
            required=required,
        )


# =============================================================
# DIRECT CONVENIENCE FUNCTION
# =============================================================

def add_student_identity_field(
    form_id: str,
    *,
    required: bool = True,
) -> ToolResult[dict[str, Any]]:
    """
    Convenience wrapper for direct usage.
    """

    tool = GoogleFormsIdentityTool()

    return tool.add_student_identity_field(
        form_id=form_id,
        required=required,
    )