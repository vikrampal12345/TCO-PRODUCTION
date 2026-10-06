from __future__ import annotations

import shutil
import sqlite3
import tempfile
from pathlib import Path

from backend.agents.evaluation_agent import EvaluationAgent
from backend.core.tool_result import ToolResult
from backend.services.assessment_result_lifecycle import (
    AssessmentResultLifecycleService,
)
from backend.services.assessment_result_service import (
    AssessmentResultService,
)
from backend.services.evaluation_cycle import EvaluationCycleService
from backend.services.result_email_service import ResultEmailService
from backend.services.result_store import ResultStore
from backend.tools.gmail import GmailTool


# =============================================================
# PROJECT CONFIGURATION
# =============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SOURCE_DB = PROJECT_ROOT / "data" / "tco.db"

EXPECTED_TEST_EMAIL = "electrofact3@gmail.com"

EXPECTED_STUDENT_NO = "GMAIL_TEST_001"

TEST_FORM_ID = "REAL_GMAIL_TEST_FORM"

TEST_RESPONSE_ID = "REAL_GMAIL_INTEGRATION_001"

TEST_ASSESSMENT_ID = 10

TEST_ATTEMPT_NUMBER = 100


# =============================================================
# FAKE GOOGLE FORMS METADATA TOOL
# =============================================================

class FakeMetadataTool:
    """
    Fake Google Forms metadata tool.

    Only the external Google Forms API is mocked.

    The following remain REAL:
    - EvaluationCycleService
    - EvaluationAgent
    - StudentIdentityResolver
    - AssessmentResultService
    - ResultStore
    - AssessmentResultLifecycleService
    - ResultEmailService
    - GmailTool
    """

    def get_metadata(
        self,
        *,
        form_id: str,
    ) -> dict:

        return {
            "form_id": form_id,

            "title": "TCO Real Gmail Test",

            "description": (
                "Real Gmail API integration test"
            ),

            "quiz_state": True,

            "responder_url": (
                "https://docs.google.com/forms/"
                "d/REAL_GMAIL_TEST_FORM/viewform"
            ),

            "revision_id": "REAL_GMAIL_REVISION",

            "question_count": 2,

            "questions": [
                {
                    "item_id": "identity-item",
                    "question_id": "identity-question",
                    "title": "Student ID / Roll Number",
                    "required": True,
                    "question_type": "text",
                    "identity_type": (
                        "student_id_or_roll_number"
                    ),
                    "raw_item": {},
                    "raw_question": {},
                },
                {
                    "item_id": "item-q1",
                    "question_id": "q1",
                    "title": "Question 1",
                    "required": True,
                    "question_type": "multiple_choice",
                    "raw_item": {},
                    "raw_question": {},
                },
                {
                    "item_id": "item-q2",
                    "question_id": "q2",
                    "title": "Question 2",
                    "required": True,
                    "question_type": "multiple_choice",
                    "raw_item": {},
                    "raw_question": {},
                },
            ],

            "answer_key": {
                "q1": [
                    "Arithmetic shift left (ASL)"
                ],
                "q2": [
                    "Correct answer"
                ],
            },

            "marking_scheme": {
                "q1": 2.5,
                "q2": 2.5,
            },

            "identity_field_count": 1,

            "identity_fields": [
                {
                    "item_id": "identity-item",
                    "question_id": "identity-question",
                    "title": "Student ID / Roll Number",
                    "required": True,
                    "question_type": "text",
                    "identity_type": (
                        "student_id_or_roll_number"
                    ),
                    "raw_item": {},
                    "raw_question": {},
                }
            ],
        }

    def execute(
        self,
        *,
        operation: str,
        **kwargs,
    ) -> ToolResult:

        if operation in {
            "form.metadata.get",
            "forms.get_metadata",
            "forms.metadata",
        }:

            metadata = self.get_metadata(
                **kwargs
            )

            return ToolResult.ok(
                data=metadata,
                metadata={
                    "tool": "fake_google_forms_metadata",
                    "operation": operation,
                },
            )

        return ToolResult.failure(
            "UNSUPPORTED_OPERATION",
            (
                "Unsupported fake metadata operation: "
                f"{operation}"
            ),
        )


# =============================================================
# FAKE GOOGLE FORMS RESPONSE TOOL
# =============================================================

class FakeResponseTool:
    """
    Fake Google Forms response tool.

    Only Google Forms responses are mocked.
    """

    def list_responses(
        self,
        *,
        form_id: str,
        page_size: int = 100,
        page_token: str | None = None,
    ) -> dict:

        return {
            "form_id": form_id,

            "responses": [
                {
                    "response_id": TEST_RESPONSE_ID,

                    "create_time": (
                        "2026-10-05T15:00:00Z"
                    ),

                    "submitted_at": (
                        "2026-10-05T15:05:00Z"
                    ),

                    "respondent_email": (
                        EXPECTED_TEST_EMAIL
                    ),

                    "answers": [
                        {
                            "question_id": (
                                "identity-question"
                            ),
                            "values": [
                                EXPECTED_STUDENT_NO
                            ],
                        },
                        {
                            "question_id": "q1",
                            "values": [
                                "Arithmetic shift left (ASL)"
                            ],
                        },
                        {
                            "question_id": "q2",
                            "values": [
                                "Wrong answer"
                            ],
                        },
                    ],
                }
            ],

            "next_page_token": None,
        }

    def get_response(
        self,
        *,
        form_id: str,
        response_id: str,
    ) -> dict:

        response_data = self.list_responses(
            form_id=form_id
        )

        for response in response_data[
            "responses"
        ]:

            if (
                response["response_id"]
                == response_id
            ):
                return response

        raise ValueError(
            f"Response not found: {response_id}"
        )

    def execute(
        self,
        *,
        operation: str,
        **kwargs,
    ) -> ToolResult:

        if operation in {
            "form.responses.list",
            "forms.list_responses",
            "forms.responses.list",
        }:

            data = self.list_responses(
                **kwargs
            )

            return ToolResult.ok(
                data=data,
                metadata={
                    "tool": "fake_google_forms_responses",
                    "operation": operation,
                },
            )

        if operation in {
            "form.responses.get",
            "forms.get_response",
            "forms.responses.get",
        }:

            data = self.get_response(
                **kwargs
            )

            return ToolResult.ok(
                data=data,
                metadata={
                    "tool": "fake_google_forms_responses",
                    "operation": operation,
                },
            )

        return ToolResult.failure(
            "UNSUPPORTED_OPERATION",
            (
                "Unsupported fake response operation: "
                f"{operation}"
            ),
        )


# =============================================================
# FIND TEST STUDENT
# =============================================================

def find_test_student(
    db_path: Path,
) -> dict:

    connection = sqlite3.connect(
        str(db_path)
    )

    connection.row_factory = sqlite3.Row

    try:

        row = connection.execute(
            """
            SELECT
                id,
                student_no,
                university_roll,
                name,
                email
            FROM students
            WHERE student_no = ?
            """,
            (
                EXPECTED_STUDENT_NO,
            ),
        ).fetchone()

    finally:

        connection.close()

    if row is None:

        raise RuntimeError(
            "Test student GMAIL_TEST_001 was not "
            "found in the source database."
        )

    return dict(row)


# =============================================================
# BUILD REAL SERVICES
# =============================================================

def build_services(
    test_db: Path,
):

    # ---------------------------------------------------------
    # REAL RESULT STORE
    # ---------------------------------------------------------

    result_store = ResultStore(
        db_path=str(test_db)
    )

    # ---------------------------------------------------------
    # REAL ASSESSMENT RESULT SERVICE
    # ---------------------------------------------------------

    result_service = AssessmentResultService(
        result_store=result_store,
    )

    # ---------------------------------------------------------
    # FAKE GOOGLE FORMS
    # ---------------------------------------------------------

    metadata_tool = FakeMetadataTool()

    response_tool = FakeResponseTool()

    # ---------------------------------------------------------
    # REAL EVALUATION AGENT
    # ---------------------------------------------------------

    evaluation_agent = EvaluationAgent()

    # ---------------------------------------------------------
    # REAL EVALUATION CYCLE
    # ---------------------------------------------------------

    evaluation_cycle = EvaluationCycleService(
        metadata_tool=metadata_tool,
        response_tool=response_tool,
        evaluation_agent=evaluation_agent,
        result_service=result_service,
    )

    # ---------------------------------------------------------
    # REAL GMAIL TOOL
    # ---------------------------------------------------------

    gmail_tool = GmailTool()

    # ---------------------------------------------------------
    # REAL RESULT EMAIL SERVICE
    # ---------------------------------------------------------

    result_email_service = ResultEmailService(
        result_store=result_store,
        gmail_tool=gmail_tool,
    )

    # ---------------------------------------------------------
    # REAL RESULT LIFECYCLE
    # ---------------------------------------------------------

    lifecycle_service = (
        AssessmentResultLifecycleService(
            evaluation_cycle=evaluation_cycle,
            result_email_service=result_email_service,
        )
    )

    return (
        result_store,
        lifecycle_service,
    )


# =============================================================
# MAIN TEST
# =============================================================

def main() -> None:

    print("=" * 60)
    print(
        "TCO REAL GMAIL API INTEGRATION TEST"
    )
    print("=" * 60)

    # ---------------------------------------------------------
    # SOURCE DATABASE
    # ---------------------------------------------------------

    if not SOURCE_DB.exists():

        raise FileNotFoundError(
            f"Source DB not found: {SOURCE_DB}"
        )

    print(
        f"Source DB: {SOURCE_DB}"
    )

    # ---------------------------------------------------------
    # FIND TEST STUDENT
    # ---------------------------------------------------------

    student = find_test_student(
        SOURCE_DB
    )

    print()

    print(
        "TEST STUDENT"
    )

    print("-" * 60)

    print(
        f"Student ID: {student['id']}"
    )

    print(
        f"Student No: {student['student_no']}"
    )

    print(
        f"Name: {student['name']}"
    )

    print(
        f"Email: {student['email']}"
    )

    # ---------------------------------------------------------
    # SAFETY CHECK
    # ---------------------------------------------------------

    if (
        str(student["email"]).lower()
        != EXPECTED_TEST_EMAIL.lower()
    ):

        raise RuntimeError(
            "SAFETY CHECK FAILED: "
            "Unexpected student email."
        )

    if (
        str(student["student_no"])
        != EXPECTED_STUDENT_NO
    ):

        raise RuntimeError(
            "SAFETY CHECK FAILED: "
            "Unexpected student number."
        )

    # ---------------------------------------------------------
    # TEMPORARY DATABASE
    # ---------------------------------------------------------

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix="tco_real_gmail_test_"
        )
    )

    test_db = (
        temp_dir / "tco_test.db"
    )

    try:

        shutil.copy2(
            SOURCE_DB,
            test_db,
        )

        print()

        print(
            f"Test DB:   {test_db}"
        )

        print()

        print(
            "TEST: REAL EVALUATION -> "
            "RESULTSTORE -> REAL GMAIL"
        )

        print("-" * 60)

        # -----------------------------------------------------
        # BUILD SERVICES
        # -----------------------------------------------------

        (
            result_store,
            lifecycle_service,
        ) = build_services(
            test_db
        )

        # -----------------------------------------------------
        # RUN COMPLETE LIFECYCLE
        # -----------------------------------------------------

        lifecycle_result = (
            lifecycle_service.process_response(
                form_id=TEST_FORM_ID,

                response_id=TEST_RESPONSE_ID,

                assessment_id=TEST_ASSESSMENT_ID,

                school_id="TCO_TEST",

                class_level="TCO Test Class",

                section="TEST",

                attempt_number=TEST_ATTEMPT_NUMBER,

                page_size=100,

                send_email=True,
            )
        )

        # -----------------------------------------------------
        # LIFECYCLE RESULT
        # -----------------------------------------------------

        print()

        print(
            "Lifecycle Status:",
            lifecycle_result.get(
                "lifecycle_status"
            ),
        )

        print(
            "Identity Method:",
            lifecycle_result.get(
                "identity_method"
            ),
        )

        # -----------------------------------------------------
        # SAVED RESULT
        # -----------------------------------------------------

        saved_result = (
            lifecycle_result.get(
                "saved_result"
            )
            or {}
        )

        result_id = saved_result.get(
            "result_id"
        )

        print(
            "Result ID:",
            result_id,
        )

        if result_id is None:

            raise AssertionError(
                "No result_id returned."
            )

        result_id = int(
            result_id
        )

        # -----------------------------------------------------
        # EMAIL RESULT
        # -----------------------------------------------------

        email_result = (
            lifecycle_result.get(
                "email"
            )
            or {}
        )

        print()

        print(
            "EMAIL RESULT"
        )

        print("-" * 60)

        print(
            "Email Status:",
            email_result.get(
                "status"
            ),
        )

        print(
            "Recipient:",
            email_result.get(
                "recipient"
            ),
        )

        print(
            "Subject:",
            email_result.get(
                "subject"
            ),
        )

        # -----------------------------------------------------
        # RESULTSTORE VERIFICATION
        # -----------------------------------------------------

        stored_result = (
            result_store.get_result(
                result_id=result_id
            )
        )

        if stored_result is None:

            raise AssertionError(
                "Result was not found in ResultStore."
            )

        print()

        print(
            "RESULTSTORE VERIFICATION"
        )

        print("-" * 60)

        print(
            "DB Email Status:",
            stored_result.get(
                "result_email_status"
            ),
        )

        print(
            "Email Sent At:",
            stored_result.get(
                "result_email_sent_at"
            ),
        )

        print(
            "Student Email:",
            stored_result.get(
                "student_email"
            ),
        )

        print(
            "Obtained Marks:",
            stored_result.get(
                "obtained_marks"
            ),
        )

        print(
            "Total Marks:",
            stored_result.get(
                "total_marks"
            ),
        )

        # -----------------------------------------------------
        # VERIFY LIFECYCLE
        # -----------------------------------------------------

        if (
            lifecycle_result.get(
                "lifecycle_status"
            )
            != "result_saved_email_sent"
        ):

            raise AssertionError(
                "Lifecycle did not finish with "
                "'result_saved_email_sent'."
            )

        # -----------------------------------------------------
        # VERIFY EMAIL STATUS
        # -----------------------------------------------------

        if (
            email_result.get(
                "status"
            )
            != "sent"
        ):

            raise AssertionError(
                "Real Gmail send did not return "
                f"'sent'. Actual: {email_result}"
            )

        # -----------------------------------------------------
        # VERIFY RECIPIENT
        # -----------------------------------------------------

        if (
            email_result.get(
                "recipient"
            )
            != EXPECTED_TEST_EMAIL
        ):

            raise AssertionError(
                "Email recipient safety check failed."
            )

        # -----------------------------------------------------
        # VERIFY DATABASE EMAIL STATUS
        # -----------------------------------------------------

        if (
            stored_result.get(
                "result_email_status"
            )
            != "sent"
        ):

            raise AssertionError(
                "ResultStore email status is not 'sent'."
            )

        # -----------------------------------------------------
        # VERIFY SENT TIMESTAMP
        # -----------------------------------------------------

        if not stored_result.get(
            "result_email_sent_at"
        ):

            raise AssertionError(
                "result_email_sent_at was not populated."
            )

        # -----------------------------------------------------
        # EXTRACT REAL GMAIL MESSAGE ID
        #
        # ResultEmailService returns GmailTool's data as:
        #
        # send_data = {
        #     "total_recipients": 1,
        #     "sent_count": 1,
        #     "failed_count": 0,
        #     "sent": [
        #         {
        #             "email": "...",
        #             "message_id": "..."
        #         }
        #     ],
        #     "failed": []
        # }
        # -----------------------------------------------------

        send_data = (
            email_result.get(
                "send_data"
            )
            or {}
        )

        sent_messages = (
            send_data.get(
                "sent"
            )
            or []
        )

        if not sent_messages:

            raise AssertionError(
                "GmailTool reported success but returned "
                "no sent message details."
            )

        first_sent_message = (
            sent_messages[0]
        )

        message_id = (
            first_sent_message.get(
                "message_id"
            )
        )

        print(
            "Gmail Message ID:",
            message_id,
        )

        # -----------------------------------------------------
        # VERIFY MESSAGE ID
        # -----------------------------------------------------

        if not message_id:

            raise AssertionError(
                "Gmail API did not return a message ID."
            )

        # -----------------------------------------------------
        # VERIFY MESSAGE RECIPIENT
        # -----------------------------------------------------

        actual_message_email = (
            first_sent_message.get(
                "email"
            )
        )

        if (
            actual_message_email
            != EXPECTED_TEST_EMAIL
        ):

            raise AssertionError(
                "GmailTool returned an unexpected "
                "recipient."
            )

        # -----------------------------------------------------
        # FINAL SUCCESS
        # -----------------------------------------------------

        print()

        print(
            "SUCCESS: REAL GMAIL SEND WORKS."
        )

        print(
            "Result was saved successfully."
        )

        print(
            "Result email was sent successfully."
        )

        print(
            f"Message ID: {message_id}"
        )

        print()

        print("=" * 60)

        print(
            "REAL GMAIL INTEGRATION TEST PASSED"
        )

        print("=" * 60)

    finally:

        # -----------------------------------------------------
        # DELETE TEMPORARY DATABASE
        # -----------------------------------------------------

        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )


# =============================================================
# ENTRY POINT
# =============================================================

if __name__ == "__main__":
    main()