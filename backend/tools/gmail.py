from __future__ import annotations

import base64
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from backend.core.base_tool import BaseTool
from backend.core.tool_result import ToolResult


class GmailTool(BaseTool):
    """
    Deterministic Gmail tool for TCO.

    Responsibilities:
    - Authenticate with Google Gmail API
    - Send one email
    - Send bulk emails
    - Return message IDs

    This tool does NOT decide:
    - who should receive the email
    - whether an assessment should be sent
    - what content should be generated

    Those decisions belong to Master Agent / workflow.
    """

    name = "gmail"

    description = (
        "Sends email through the authenticated Gmail account."
    )

    capabilities = (
        "email.send",
        "email.send_bulk",
    )

    # Least-privilege Gmail scope for sending email
    SCOPES = [
        "https://www.googleapis.com/auth/gmail.send",
    ]

    def __init__(self) -> None:

        # Project root:
        # E:\TCO
        self.project_root = (
            Path(__file__).resolve().parents[2]
        )

        # Same OAuth client used for Google Forms
        self.credentials_file = (
            self.project_root / "credentials.json"
        )

        # Keep Gmail token separate from Forms token
        self.token_file = (
            self.project_root / "gmail_token.json"
        )

    # =========================================================
    # AUTHENTICATION
    # =========================================================

    def _get_credentials(self) -> Credentials:

        creds: Credentials | None = None

        # -----------------------------------------------------
        # Load existing Gmail token
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
        # Existing valid token
        # -----------------------------------------------------

        if creds and creds.valid:
            return creds

        # -----------------------------------------------------
        # Refresh expired token
        # -----------------------------------------------------

        if (
            creds
            and creds.expired
            and creds.refresh_token
        ):

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

            flow = (
                InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file),
                    self.SCOPES,
                )
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
    # GMAIL SERVICE
    # =========================================================

    def _build_service(self):

        creds = self._get_credentials()

        return build(
            "gmail",
            "v1",
            credentials=creds,
        )

    # =========================================================
    # EMAIL VALIDATION
    # =========================================================

    @staticmethod
    def _validate_email(email: str) -> str:

        email = str(email).strip()

        if not email:
            raise ValueError(
                "Recipient email cannot be empty."
            )

        if "@" not in email:

            raise ValueError(
                f"Invalid email address: {email}"
            )

        return email

    # =========================================================
    # BUILD MIME MESSAGE
    # =========================================================

    def _build_message(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        cc: str | None = None,
        bcc: str | None = None,
    ) -> dict[str, str]:

        to = self._validate_email(to)

        subject = str(subject).strip()
        body = str(body)

        if not subject:

            raise ValueError(
                "Email subject cannot be empty."
            )

        if not body.strip():

            raise ValueError(
                "Email body cannot be empty."
            )

        message = EmailMessage()

        message.set_content(body)

        message["To"] = to
        message["Subject"] = subject

        if cc:

            message["Cc"] = (
                self._validate_email(cc)
            )

        if bcc:

            message["Bcc"] = (
                self._validate_email(bcc)
            )

        encoded_message = (
            base64.urlsafe_b64encode(
                message.as_bytes()
            )
            .decode("utf-8")
        )

        return {
            "raw": encoded_message,
        }

    # =========================================================
    # SEND ONE EMAIL
    # =========================================================

    def send_email(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        cc: str | None = None,
        bcc: str | None = None,
    ) -> ToolResult:

        try:

            service = self._build_service()

            message = self._build_message(
                to=to,
                subject=subject,
                body=body,
                cc=cc,
                bcc=bcc,
            )

            result = (
                service.users()
                .messages()
                .send(
                    userId="me",
                    body=message,
                )
                .execute()
            )

            return ToolResult.ok(
                data={
                    "message_id": result.get(
                        "id"
                    ),
                    "thread_id": result.get(
                        "threadId"
                    ),
                    "to": to,
                    "subject": subject,
                },
                metadata={
                    "tool": self.name,
                    "operation": "email.send",
                },
            )

        except FileNotFoundError as exc:

            return ToolResult.failure(
                "GMAIL_AUTH_FAILED",
                str(exc),
            )

        except HttpError as exc:

            return ToolResult.failure(
                "GMAIL_SEND_FAILED",
                str(exc),
            )

        except ValueError as exc:

            return ToolResult.failure(
                "INVALID_EMAIL_DATA",
                str(exc),
            )

        except Exception as exc:

            return ToolResult.failure(
                "GMAIL_SEND_FAILED",
                str(exc),
            )

    # =========================================================
    # SEND BULK EMAIL
    # =========================================================

    def send_bulk(
        self,
        *,
        recipients: list[str],
        subject: str,
        body: str,
    ) -> ToolResult:

        if not isinstance(
            recipients,
            list,
        ):

            return ToolResult.failure(
                "INVALID_RECIPIENTS",
                "recipients must be a list.",
            )

        if not recipients:

            return ToolResult.failure(
                "NO_RECIPIENTS",
                "At least one recipient is required.",
            )

        # -----------------------------------------------------
        # Remove duplicate email addresses
        # -----------------------------------------------------

        unique_recipients: list[str] = []

        seen: set[str] = set()

        for recipient in recipients:

            email = self._validate_email(
                recipient
            )

            normalized = email.lower()

            if normalized not in seen:

                seen.add(normalized)

                unique_recipients.append(
                    email
                )

        sent: list[dict[str, Any]] = []
        failed: list[dict[str, Any]] = []

        # -----------------------------------------------------
        # Send individually
        # -----------------------------------------------------

        for recipient in unique_recipients:

            result = self.send_email(
                to=recipient,
                subject=subject,
                body=body,
            )

            if result.success:

                sent.append(
                    {
                        "email": recipient,
                        "message_id": (
                            result.data or {}
                        ).get(
                            "message_id"
                        ),
                    }
                )

            else:

                failed.append(
                    {
                        "email": recipient,
                        "error_code": (
                            result.error_code
                        ),
                        "error_message": (
                            result.error_message
                        ),
                    }
                )

        return ToolResult.ok(
            data={
                "total_recipients": len(
                    unique_recipients
                ),
                "sent_count": len(sent),
                "failed_count": len(failed),
                "sent": sent,
                "failed": failed,
            },
            metadata={
                "tool": self.name,
                "operation": "email.send_bulk",
            },
        )

    # =========================================================
    # GENERIC TOOL ENTRYPOINT
    # =========================================================

    def execute(
        self,
        *,
        operation: str,
        **kwargs: Any,
    ) -> ToolResult:

        operations = {
            "email.send": self.send_email,
            "email.send_bulk": self.send_bulk,
        }

        handler = operations.get(operation)

        if handler is None:

            return ToolResult.failure(
                "UNKNOWN_OPERATION",
                (
                    "Unsupported Gmail operation: "
                    f"{operation}"
                ),
            )

        return handler(**kwargs)