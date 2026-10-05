from __future__ import annotations

import shutil
import sqlite3
import tempfile
from pathlib import Path

from backend.core.tool_result import ToolResult
from backend.services.result_store import ResultStore
from backend.services.result_email_service import ResultEmailService


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SOURCE_DB = (
    PROJECT_ROOT
    / "data"
    / "tco.db"
)


# ============================================================
# FAKE GMAIL TOOL
# ============================================================

class FakeGmailTool:
    """
    Fake Gmail tool used only for testing.

    It does NOT send any real email.
    """

    def __init__(
        self,
        *,
        should_fail: bool = False,
    ) -> None:
        self.should_fail = should_fail

        self.calls: list[dict] = []

    def execute(
        self,
        *,
        operation: str,
        **kwargs,
    ):
        self.calls.append(
            {
                "operation": operation,
                **kwargs,
            }
        )

        # ----------------------------------------------------
        # Simulate Gmail failure
        # ----------------------------------------------------

        if self.should_fail:
            return ToolResult.failure(
                error_code="SIMULATED_GMAIL_FAILURE",
                error_message="Simulated Gmail failure.",
            )

        # ----------------------------------------------------
        # Simulate successful Gmail send
        # ----------------------------------------------------

        recipients = kwargs.get(
            "recipients",
            [],
        )

        return ToolResult.ok(
            data={
                "status": "sent",
                "total_recipients": len(
                    recipients
                ),
                "sent_count": len(
                    recipients
                ),
                "failed_count": 0,
            }
        )


# ============================================================
# CREATE TEMPORARY TEST DATABASE
# ============================================================

def create_test_database():
    """
    Create an isolated temporary copy of the real TCO database.

    The real data/tco.db is never modified.
    """

    if not SOURCE_DB.exists():
        raise FileNotFoundError(
            f"Source database not found: {SOURCE_DB}"
        )

    temp_dir = tempfile.TemporaryDirectory(
        prefix="tco_result_email_"
    )

    test_db = (
        Path(temp_dir.name)
        / "tco_test.db"
    )

    shutil.copy2(
        SOURCE_DB,
        test_db,
    )

    return test_db, temp_dir


# ============================================================
# GET TEST STUDENT
# ============================================================

def get_test_student(
    result_store: ResultStore,
) -> dict:
    """
    Get the known Gmail test student.

    We use a separate SQLite connection here because
    ResultStore intentionally does not expose a public
    'conn' attribute.
    """

    connection = sqlite3.connect(
        result_store.db_path
    )

    connection.row_factory = sqlite3.Row

    try:
        student = connection.execute(
            """
            SELECT
                id,
                student_no,
                university_roll,
                name,
                email,
                school_id,
                class_level,
                section
            FROM students
            WHERE email = ?
            LIMIT 1
            """,
            (
                "electrofact3@gmail.com",
            ),
        ).fetchone()

    finally:
        connection.close()

    if student is None:
        raise RuntimeError(
            "Test student "
            "electrofact3@gmail.com "
            "was not found."
        )

    return {
        "id": student["id"],
        "student_no": student["student_no"],
        "university_roll": student[
            "university_roll"
        ],
        "name": student["name"],
        "email": student["email"],
        "school_id": student[
            "school_id"
        ],
        "class_level": student[
            "class_level"
        ],
        "section": student[
            "section"
        ],
    }


# ============================================================
# GET TEST ASSESSMENT
# ============================================================

def get_test_assessment(
    result_store: ResultStore,
) -> dict:
    """
    Get the existing assessment used by the test.
    """

    connection = sqlite3.connect(
        result_store.db_path
    )

    connection.row_factory = sqlite3.Row

    try:
        assessment = connection.execute(
            """
            SELECT
                id,
                title,
                subject,
                topic
            FROM assessments
            WHERE id = ?
            LIMIT 1
            """,
            (10,),
        ).fetchone()

    finally:
        connection.close()

    if assessment is None:
        raise RuntimeError(
            "Test assessment with ID 10 "
            "was not found."
        )

    return {
        "id": assessment["id"],
        "title": assessment["title"],
        "subject": assessment[
            "subject"
        ],
        "topic": assessment[
            "topic"
        ],
    }


# ============================================================
# CREATE TEST RESULT
# ============================================================

def create_test_result(
    result_store: ResultStore,
    *,
    student_id: int,
    assessment_id: int,
    attempt_number: int = 99,
    form_response_id: str = (
        "RESULT_EMAIL_TEST_RESPONSE"
    ),
) -> dict:
    """
    Create a result using the real ResultStore API.

    Important:
    ResultStore itself gets student_name and
    student_email from the students table.
    """

    saved = result_store.save_result(
        assessment_id=assessment_id,
        student_id=student_id,
        attempt_number=attempt_number,

        submitted_at=(
            "2026-10-05T15:00:00Z"
        ),

        obtained_marks=2.5,
        total_marks=5.0,

        correct_answers=1,
        wrong_answers=1,
        unanswered=0,

        status="evaluated",

        form_response_id=(
            form_response_id
        ),

        answers_json=(
            '{"q1":"Arithmetic shift left (ASL)",'
            '"q2":"Wrong answer"}'
        ),

        question_results_json=(
            '[{"question_id":"q1",'
            '"correct":true,'
            '"marks_awarded":2.5},'
            '{"question_id":"q2",'
            '"correct":false,'
            '"marks_awarded":0}]'
        ),
    )

    return saved


# ============================================================
# TEST 1
# SUCCESSFUL EMAIL SEND
# ============================================================

def test_send_result(
    result_store: ResultStore,
    result_id: int,
) -> None:
    """
    Test successful result email sending.
    """

    gmail_tool = FakeGmailTool()

    service = ResultEmailService(
        result_store=result_store,
        gmail_tool=gmail_tool,
    )

    outcome = service.send_result(
        result_id=result_id
    )

    # --------------------------------------------------------
    # Assertions
    # --------------------------------------------------------

    assert outcome["status"] == "sent"

    assert (
        outcome["result_id"]
        == result_id
    )

    assert (
        outcome["recipient"]
        == "electrofact3@gmail.com"
    )

    # Gmail should have been called exactly once.

    assert len(
        gmail_tool.calls
    ) == 1

    call = gmail_tool.calls[0]

    assert (
        call["operation"]
        == "email.send_bulk"
    )

    assert call["recipients"] == [
        "electrofact3@gmail.com"
    ]

    assert (
        "TCO Assessment Result"
        in call["subject"]
    )

    # --------------------------------------------------------
    # Check email body
    # --------------------------------------------------------

    assert (
        "Marks:"
        in call["body"]
    )

    assert (
        "Percentage:"
        in call["body"]
    )

    assert (
        "Correct Answers:"
        in call["body"]
    )

    assert (
        "Wrong Answers:"
        in call["body"]
    )

    assert (
        "Unanswered:"
        in call["body"]
    )

    # --------------------------------------------------------
    # Check database
    # --------------------------------------------------------

    saved_result = (
        result_store.get_result(
            result_id=result_id
        )
    )

    assert saved_result is not None

    assert (
        saved_result[
            "result_email_status"
        ]
        == "sent"
    )

    assert (
        saved_result[
            "result_email_sent_at"
        ]
        is not None
    )

    print(
        "SUCCESS: Result email sent successfully."
    )

    print(
        f"Recipient: "
        f"{outcome['recipient']}"
    )

    print(
        f"Subject: "
        f"{outcome['subject']}"
    )


# ============================================================
# TEST 2
# DUPLICATE EMAIL PROTECTION
# ============================================================

def test_duplicate_protection(
    result_store: ResultStore,
    result_id: int,
) -> None:
    """
    A result already marked as sent should not
    be sent again unless force=True.
    """

    gmail_tool = FakeGmailTool()

    service = ResultEmailService(
        result_store=result_store,
        gmail_tool=gmail_tool,
    )

    outcome = service.send_result(
        result_id=result_id
    )

    # --------------------------------------------------------
    # Assertions
    # --------------------------------------------------------

    assert (
        outcome["status"]
        == "already_sent"
    )

    assert (
        outcome["result_id"]
        == result_id
    )

    # Gmail must NOT be called again.

    assert len(
        gmail_tool.calls
    ) == 0

    print(
        "SUCCESS: "
        "Duplicate email protection works."
    )


# ============================================================
# TEST 3
# GMAIL FAILURE
# ============================================================

def test_gmail_failure(
    result_store: ResultStore,
    *,
    student_id: int,
    assessment_id: int,
) -> None:
    """
    Test Gmail failure handling.

    IMPORTANT:
    We use attempt_number=100 so this is a
    completely new result.

    The previous successful test uses attempt_number=99.
    """

    saved = create_test_result(
        result_store,

        student_id=student_id,

        assessment_id=assessment_id,

        attempt_number=100,

        form_response_id=(
            "RESULT_EMAIL_FAILURE_TEST_RESPONSE"
        ),
    )

    result_id = int(
        saved["result_id"]
    )

    # --------------------------------------------------------
    # Fake Gmail configured to fail
    # --------------------------------------------------------

    gmail_tool = FakeGmailTool(
        should_fail=True
    )

    service = ResultEmailService(
        result_store=result_store,
        gmail_tool=gmail_tool,
    )

    outcome = service.send_result(
        result_id=result_id
    )

    # --------------------------------------------------------
    # Assertions
    # --------------------------------------------------------

    assert (
        outcome["status"]
        == "failed"
    )

    assert (
        outcome["result_id"]
        == result_id
    )

    assert (
        outcome["recipient"]
        == "electrofact3@gmail.com"
    )

    assert (
        "Simulated Gmail failure"
        in outcome["error"]
    )

    # --------------------------------------------------------
    # Check database status
    # --------------------------------------------------------

    updated_result = (
        result_store.get_result(
            result_id=result_id
        )
    )

    assert updated_result is not None

    assert (
        updated_result[
            "result_email_status"
        ]
        == "failed"
    )

    assert (
        updated_result[
            "result_email_error"
        ]
        == "Simulated Gmail failure."
    )

    print(
        "SUCCESS: "
        "Gmail failure handling works."
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    print("=" * 60)

    print(
        "TCO RESULT EMAIL SERVICE TEST"
    )

    print("=" * 60)

    print()

    print(
        f"Source DB: {SOURCE_DB}"
    )

    # --------------------------------------------------------
    # Create temporary DB
    # --------------------------------------------------------

    test_db, temp_dir = (
        create_test_database()
    )

    result_store = None

    try:

        print(
            f"Test DB:   {test_db}"
        )

        # ----------------------------------------------------
        # ResultStore
        # ----------------------------------------------------

        result_store = ResultStore(
            db_path=str(test_db)
        )

        # ----------------------------------------------------
        # TEST STUDENT
        # ----------------------------------------------------

        student = get_test_student(
            result_store
        )

        print()

        print(
            "TEST STUDENT"
        )

        print(
            "-" * 60
        )

        print(
            f"Student ID: "
            f"{student['id']}"
        )

        print(
            f"Student No: "
            f"{student['student_no']}"
        )

        print(
            f"Student Name: "
            f"{student['name']}"
        )

        print(
            f"Student Email: "
            f"{student['email']}"
        )

        # ----------------------------------------------------
        # TEST ASSESSMENT
        # ----------------------------------------------------

        assessment = (
            get_test_assessment(
                result_store
            )
        )

        print()

        print(
            "TEST ASSESSMENT"
        )

        print(
            "-" * 60
        )

        print(
            f"Assessment ID: "
            f"{assessment['id']}"
        )

        print(
            f"Title: "
            f"{assessment['title']}"
        )

        print(
            f"Subject: "
            f"{assessment['subject']}"
        )

        print(
            f"Topic: "
            f"{assessment['topic']}"
        )

        # ----------------------------------------------------
        # CREATE INITIAL RESULT
        # ----------------------------------------------------

        saved = create_test_result(
            result_store,

            student_id=student["id"],

            assessment_id=assessment["id"],

            attempt_number=99,

            form_response_id=(
                "RESULT_EMAIL_TEST_RESPONSE"
            ),
        )

        result_id = int(
            saved["result_id"]
        )

        print()

        print(
            "TEST RESULT"
        )

        print(
            "-" * 60
        )

        print(
            f"Result ID: "
            f"{result_id}"
        )

        print(
            f"Obtained: "
            f"{saved['obtained_marks']}"
        )

        print(
            f"Total: "
            f"{saved['total_marks']}"
        )

        print(
            f"Percentage: "
            f"{saved['percentage']}"
        )

        print(
            f"Correct: "
            f"{saved['correct_answers']}"
        )

        print(
            f"Wrong: "
            f"{saved['wrong_answers']}"
        )

        print(
            f"Unanswered: "
            f"{saved['unanswered']}"
        )

        print(
            f"Email Status: "
            f"{saved['result_email_status']}"
        )

        # ----------------------------------------------------
        # TEST 1
        # ----------------------------------------------------

        print()

        print(
            "TEST 1: SEND RESULT"
        )

        print(
            "-" * 60
        )

        test_send_result(
            result_store,
            result_id,
        )

        # ----------------------------------------------------
        # TEST 2
        # ----------------------------------------------------

        print()

        print(
            "TEST 2: DUPLICATE PROTECTION"
        )

        print(
            "-" * 60
        )

        test_duplicate_protection(
            result_store,
            result_id,
        )

        # ----------------------------------------------------
        # TEST 3
        # ----------------------------------------------------

        print()

        print(
            "TEST 3: GMAIL FAILURE"
        )

        print(
            "-" * 60
        )

        test_gmail_failure(
            result_store,

            student_id=student["id"],

            assessment_id=assessment["id"],
        )

        # ----------------------------------------------------
        # FINAL SUCCESS
        # ----------------------------------------------------

        print()

        print(
            "=" * 60
        )

        print(
            "ALL RESULT EMAIL SERVICE TESTS PASSED"
        )

        print(
            "=" * 60
        )

    finally:

        # ----------------------------------------------------
        # Important for Windows:
        # remove references to ResultStore before
        # deleting the temporary SQLite database.
        # ----------------------------------------------------

        result_store = None

        # Give Python a chance to release local
        # references before Windows cleanup.

        try:
            temp_dir.cleanup()

        except PermissionError:

            print()

            print(
                "WARNING: Temporary database "
                "could not be removed immediately."
            )

            print(
                "This does not affect the test result."
            )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()