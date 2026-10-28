from __future__ import annotations

import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DB = PROJECT_ROOT / "data" / "tco.db"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class FakeMetadataTool:
    def execute(
        self,
        operation: str,
        *,
        form_id: str,
    ):
        from backend.core.tool_result import ToolResult

        questions = [
            {
                "question_id": "q1",
                "question": "Which operation is ASL?",
                "question_type": "radio",
                "options": [
                    "Logical shift right",
                    "Arithmetic shift left (ASL)",
                    "Rotate left",
                    "Arithmetic shift right",
                ],
                "marks": 2.5,
            },
            {
                "question_id": "q2",
                "question": "What action occurs for bit pair 10?",
                "question_type": "radio",
                "options": [
                    "Add M then ASR",
                    "Subtract M then ASR",
                    "ASR only",
                    "No operation",
                ],
                "marks": 2.5,
            },
        ]

        answer_key = [
            {
                "question_id": "q1",
                "correct_answers": ["Arithmetic shift left (ASL)"],
                "accepted_answers": ["Arithmetic shift left (ASL)"],
                "correct_option": 2,
                "marks": 2.5,
                "points": 2.5,
            },
            {
                "question_id": "q2",
                "correct_answers": ["Add M then ASR"],
                "accepted_answers": ["Add M then ASR"],
                "correct_option": 1,
                "marks": 2.5,
                "points": 2.5,
            },
        ]

        return ToolResult.ok(
            data={
                "form_id": form_id,
                "title": "Result Email Integration Test Form",
                "identity_fields": [
                    {
                        "item_id": "identity-item",
                        "question_id": "identity-question",
                        "title": "Student ID / Roll Number",
                        "required": True,
                        "question_type": "text",
                        "identity_type": "student_id_or_roll_number",
                    }
                ],
                "questions": questions,
                "answer_key": answer_key,
                "marking_scheme": [
                    {"question_id": "q1", "max_marks": 2.5},
                    {"question_id": "q2", "max_marks": 2.5},
                ],
            }
        )


class FakeResponseTool:
    def __init__(self, *, response_id: str):
        self.response_id = response_id

    def execute(
        self,
        operation: str,
        *,
        form_id: str,
        page_size: int = 100,
    ):
        from backend.core.tool_result import ToolResult

        return ToolResult.ok(
            data={
                "responses": [
                    {
                        "form_id": form_id,
                        "response_id": self.response_id,
                        "submitted_at": "2026-10-05T15:00:00Z",
                        "respondent_email": "electrofact3@gmail.com",
                        "answers": [
                            {
                                "question_id": "identity-question",
                                "values": ["GMAIL_TEST_001"],
                            },
                            {
                                "question_id": "q1",
                                "values": [
                                    "Arithmetic shift left (ASL)"
                                ],
                            },
                            {
                                "question_id": "q2",
                                "values": ["Wrong answer"],
                            },
                        ],
                    }
                ]
            }
        )


class FakeGmailTool:
    def __init__(self, *, should_fail: bool = False):
        self.should_fail = should_fail
        self.calls: list[dict] = []

    def execute(
        self,
        operation: str,
        *,
        recipients: list[str],
        subject: str,
        body: str,
    ):
        from backend.core.tool_result import ToolResult

        self.calls.append(
            {
                "operation": operation,
                "recipients": recipients,
                "subject": subject,
                "body": body,
            }
        )

        if self.should_fail:
            return ToolResult.failure(
                error_code="SIMULATED_GMAIL_FAILURE",
                error_message="Simulated Gmail failure."
            )

        return ToolResult.ok(
            data={
                "accepted": recipients,
                "message_id": "FAKE_GMAIL_MESSAGE_001",
            }
        )


def find_test_student(db_path: Path) -> dict:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row

    try:
        row = connection.execute(
            """
            SELECT
                id,
                student_no,
                university_roll,
                name,
                email,
                class_level,
                section,
                school_id
            FROM students
            WHERE student_no = ?
            LIMIT 1
            """,
            ("GMAIL_TEST_001",),
        ).fetchone()

        if row is None:
            raise RuntimeError(
                "Known test student GMAIL_TEST_001 was not found."
            )

        return dict(row)
    finally:
        connection.close()


def seed_test_records(db_path: Path) -> None:
    """Seed only the isolated records used by this fake-provider fixture."""
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO students (
                student_no, university_roll, name, email,
                class_level, section, school_id,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "GMAIL_TEST_001",
                "GMAIL_TEST_001",
                "Controlled Result Email Student",
                "electrofact3@gmail.com",
                "TCO Test Class",
                "TEST",
                "TCO_TEST",
                "2026-10-05T00:00:00Z",
                "2026-10-05T00:00:00Z",
            ),
        )
        connection.execute(
            """
            INSERT INTO assessments (
                id, title, subject, topic, class_level, section,
                total_marks, question_count, generation_mode,
                form_id, responder_url, status, created_by, school_id,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                10,
                "Result Email Integration Assessment",
                "Computer Science",
                "Booth Algorithm",
                "TCO Test Class",
                "TEST",
                5,
                2,
                "test_fixture",
                "result-email-integration-form",
                "https://example.test/forms/result-email-integration-form",
                "published",
                "TCO_TEST_TEACHER",
                "TCO_TEST",
                "2026-10-05T00:00:00Z",
                "2026-10-05T00:00:00Z",
            ),
        )
        connection.commit()


def build_services(
    *,
    test_db: Path,
    response_id: str,
    gmail_should_fail: bool = False,
):
    from backend.agents.evaluation_agent import EvaluationAgent
    from backend.services.assessment_result_lifecycle import (
        AssessmentResultLifecycleService,
    )
    from backend.services.assessment_result_service import (
        AssessmentResultService,
    )
    from backend.services.evaluation_cycle import EvaluationCycleService
    from backend.services.result_email_service import ResultEmailService
    from backend.services.result_store import ResultStore
    from backend.services.student_identity import StudentIdentityResolver

    result_store = ResultStore(db_path=test_db)

    identity_resolver = StudentIdentityResolver(
        db_path=test_db
    )

    result_service = AssessmentResultService(
        result_store=result_store,
        identity_resolver=identity_resolver,
    )

    evaluation_cycle = EvaluationCycleService(
        metadata_tool=FakeMetadataTool(),
        response_tool=FakeResponseTool(
            response_id=response_id
        ),
        evaluation_agent=EvaluationAgent(model=object()),
        result_service=result_service,
    )

    gmail_tool = FakeGmailTool(
        should_fail=gmail_should_fail
    )

    result_email_service = ResultEmailService(
        result_store=result_store,
        gmail_tool=gmail_tool,
    )

    lifecycle_service = AssessmentResultLifecycleService(
        evaluation_cycle=evaluation_cycle,
        result_email_service=result_email_service,
    )

    return (
        lifecycle_service,
        result_store,
        gmail_tool,
    )


def main() -> int:
    print("=" * 60)
    print("TCO REAL RESULT -> EMAIL INTEGRATION TEST")
    print("=" * 60)

    if not SOURCE_DB.exists():
        raise RuntimeError(
            f"Database not found: {SOURCE_DB}"
        )

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix="tco_result_email_integration_"
        )
    )
    test_db = temp_dir / "tco_test.db"

    shutil.copy2(SOURCE_DB, test_db)
    seed_test_records(test_db)

    print("Source DB:", SOURCE_DB)
    print("Test DB:  ", test_db)

    try:
        student = find_test_student(test_db)

        print("\nTEST STUDENT")
        print("-" * 60)
        print("Student ID:", student["id"])
        print("Student No:", student["student_no"])
        print("Name:", student["name"])
        print("Email:", student["email"])

        # ----------------------------------------------------
        # TEST 1: REAL SERVICES + SUCCESSFUL EMAIL
        # ----------------------------------------------------
        print("\nTEST 1: REAL EVALUATION -> RESULTSTORE -> EMAIL")
        print("-" * 60)

        lifecycle_service, result_store, gmail_tool = build_services(
            test_db=test_db,
            response_id="RESULT_EMAIL_INTEGRATION_001",
            gmail_should_fail=False,
        )

        results = lifecycle_service.process_form(
            form_id="result-email-integration-form",
            assessment_id=10,
            school_id="TCO_TEST",
            class_level="TCO Test Class",
            section="TEST",
            attempt_number=98,
            send_email=True,
        )

        assert len(results) == 1

        lifecycle = results[0]

        assert lifecycle["lifecycle_status"] == (
            "result_saved_email_sent"
        )

        assert lifecycle["status"] == "saved"

        evaluation = lifecycle["evaluation_result"]

        assert evaluation["student_identifier"] == (
            student["student_no"]
        )

        assert evaluation["identity_status"] == "captured"

        assert evaluation["identity_field"]["question_id"] == (
            "identity-question"
        )

        assessment_answer_ids = {
            answer["question_id"]
            for answer in evaluation["answers"]
        }

        assert assessment_answer_ids == {"q1", "q2"}

        assert "identity-question" not in assessment_answer_ids

        saved_result = lifecycle["saved_result"]
        result_id = int(saved_result["result_id"])

        assert result_id > 0

        assert lifecycle["email"]["status"] == "sent"

        assert len(gmail_tool.calls) == 1

        assert gmail_tool.calls[0]["recipients"] == [
            "electrofact3@gmail.com"
        ]

        stored_result = result_store.get_result(
            result_id=result_id
        )

        assert stored_result is not None

        assert stored_result["result_email_status"] == "sent"

        assert stored_result["form_response_id"] == (
            "RESULT_EMAIL_INTEGRATION_001"
        )

        print("SUCCESS: Real result save + email flow works.")
        print("Result ID:", result_id)
        print("Identity Method:", lifecycle["identity_method"])
        print("Email Status:", stored_result["result_email_status"])

        # ----------------------------------------------------
        # TEST 2: EMAIL FAILURE MUST NOT DELETE RESULT
        # ----------------------------------------------------
        print("\nTEST 2: EMAIL FAILURE AFTER RESULT SAVE")
        print("-" * 60)

        (
            lifecycle_service,
            result_store,
            gmail_tool,
        ) = build_services(
            test_db=test_db,
            response_id="RESULT_EMAIL_INTEGRATION_002",
            gmail_should_fail=True,
        )

        results = lifecycle_service.process_form(
            form_id="result-email-integration-form-failure",
            assessment_id=10,
            school_id="TCO_TEST",
            class_level="TCO Test Class",
            section="TEST",
            attempt_number=97,
            send_email=True,
        )

        assert len(results) == 1

        lifecycle = results[0]

        assert lifecycle["lifecycle_status"] == (
            "result_saved_email_failed"
        )

        assert lifecycle["status"] == "saved"

        result_id = int(
            lifecycle["saved_result"]["result_id"]
        )

        stored_result = result_store.get_result(
            result_id=result_id
        )

        assert stored_result is not None

        assert stored_result["result_email_status"] == "failed"

        assert stored_result["result_email_error"] == (
            "Simulated Gmail failure."
        )

        assert len(gmail_tool.calls) == 1

        print(
            "SUCCESS: Email failure does not affect saved result."
        )
        print("Result ID:", result_id)
        print("Email Status:", stored_result["result_email_status"])
        print("Email Error:", stored_result["result_email_error"])

        # ----------------------------------------------------
        # FINAL
        # ----------------------------------------------------
        print("\n" + "=" * 60)
        print("ALL REAL RESULT -> EMAIL INTEGRATION TESTS PASSED")
        print("=" * 60)

        return 0

    finally:
        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )


if __name__ == "__main__":
    raise SystemExit(main())
