from __future__ import annotations

import shutil
import sqlite3
import tempfile
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
)

SOURCE_DB = (
    PROJECT_ROOT
    / "data"
    / "tco.db"
)


class FakeMetadataTool:
    """
    Fake Google Forms metadata source.

    Includes:
        - 3 identity fields
        - 2 assessment questions

    Identity fields must never appear inside
    the assessment question list.
    """

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
                "question": (
                    "Which operation is ASL?"
                ),
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
                "question": (
                    "What action occurs for bit pair 10?"
                ),
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
                "correct_answers": [
                    "Arithmetic shift left (ASL)"
                ],
                "accepted_answers": [
                    "Arithmetic shift left (ASL)"
                ],
                "correct_option": 2,
                "marks": 2.5,
                "points": 2.5,
            },
            {
                "question_id": "q2",
                "correct_answers": [
                    "Add M then ASR"
                ],
                "accepted_answers": [
                    "Add M then ASR"
                ],
                "correct_option": 1,
                "marks": 2.5,
                "points": 2.5,
            },
        ]

        identity_fields = [
            {
                "item_id": "name-item",
                "question_id": "name-question",
                "title": "Student Name",
                "required": True,
                "question_type": "text",
                "identity_type": "student_name",
            },
            {
                "item_id": "identity-item",
                "question_id": "identity-question",
                "title": "Student ID / Roll Number",
                "required": True,
                "question_type": "text",
                "identity_type": (
                    "student_id_or_roll_number"
                ),
            },
            {
                "item_id": "email-item",
                "question_id": "email-question",
                "title": "Email ID",
                "required": True,
                "question_type": "text",
                "identity_type": "student_email",
            },
        ]

        return ToolResult.ok(
            data={
                "form_id": form_id,
                "title": "Integration Test Form",
                "questions": questions,
                "answer_key": answer_key,
                "marking_scheme": [
                    {
                        "question_id": "q1",
                        "max_marks": 2.5,
                    },
                    {
                        "question_id": "q2",
                        "max_marks": 2.5,
                    },
                ],
                "identity_field_count": len(
                    identity_fields
                ),
                "identity_fields": identity_fields,
            }
        )


class FakeResponseTool:
    """
    Fake Google Forms response source.

    The identity values are returned as normal
    Google Forms answer entries so that
    EvaluationCycleService must separate them.
    """

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
                        "response_id": (
                            "INTEGRATION_RESPONSE_001"
                        ),
                        "submitted_at": (
                            "2026-10-05T15:00:00Z"
                        ),

                        # Keep this as a fallback value.
                        # The explicit Email ID question
                        # should take priority.
                        "respondent_email": (
                            "fallback@example.com"
                        ),

                        "answers": [
                            {
                                "question_id": (
                                    "name-question"
                                ),
                                "values": [
                                    "electro"
                                ],
                            },
                            {
                                "question_id": (
                                    "identity-question"
                                ),
                                "values": [
                                    "GMAIL_TEST_001"
                                ],
                            },
                            {
                                "question_id": (
                                    "email-question"
                                ),
                                "values": [
                                    "electrofact3@gmail.com"
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
                ]
            }
        )


def find_test_student(
    db_path: Path,
) -> dict:
    connection = sqlite3.connect(
        db_path
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
                email,
                class_level,
                section,
                school_id
            FROM students
            WHERE email = ?
            LIMIT 1
            """,
            (
                "electrofact3@gmail.com",
            ),
        ).fetchone()

        if row is None:
            raise RuntimeError(
                "Known test student was not found."
            )

        return dict(row)

    finally:
        connection.close()


def main() -> int:
    print("=" * 60)
    print(
        "TCO EVALUATION -> IDENTITY -> RESULTSTORE TEST"
    )
    print("=" * 60)

    if not SOURCE_DB.exists():
        raise RuntimeError(
            f"Database not found: {SOURCE_DB}"
        )

    # --------------------------------------------------------
    # Temporary database
    # --------------------------------------------------------

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix="tco_eval_integration_"
        )
    )

    test_db = (
        temp_dir
        / "tco_test.db"
    )

    shutil.copy2(
        SOURCE_DB,
        test_db,
    )

    print(
        "Source DB:",
        SOURCE_DB,
    )

    print(
        "Test DB:  ",
        test_db,
    )

    try:
        # ----------------------------------------------------
        # Find known test student
        # ----------------------------------------------------

        student = find_test_student(
            test_db
        )

        print("\nTEST STUDENT")
        print("-" * 60)

        print(
            "Student ID:",
            student["id"],
        )

        print(
            "Student No:",
            student["student_no"],
        )

        print(
            "Name:",
            student["name"],
        )

        print(
            "Email:",
            student["email"],
        )

        print(
            "School:",
            student["school_id"],
        )

        # ----------------------------------------------------
        # Imports
        # ----------------------------------------------------

        from backend.agents.evaluation_agent import (
            EvaluationAgent,
        )

        from backend.services.assessment_result_service import (
            AssessmentResultService,
        )

        from backend.services.evaluation_cycle import (
            EvaluationCycleService,
        )

        from backend.services.result_store import (
            ResultStore,
        )

        from backend.services.student_identity import (
            StudentIdentityResolver,
        )

        # ----------------------------------------------------
        # Build services using temporary DB
        # ----------------------------------------------------

        result_store = ResultStore(
            db_path=test_db
        )

        identity_resolver = (
            StudentIdentityResolver(
                db_path=test_db
            )
        )

        result_service = (
            AssessmentResultService(
                result_store=result_store,
                identity_resolver=identity_resolver,
            )
        )

        evaluation_service = (
            EvaluationCycleService(
                metadata_tool=FakeMetadataTool(),
                response_tool=FakeResponseTool(),
                evaluation_agent=EvaluationAgent(
                    model=object()
                ),
                result_service=result_service,
            )
        )

        # ----------------------------------------------------
        # Full lifecycle
        #
        # Google Form
        #     ↓
        # Identity separation
        #     ↓
        # Evaluation Agent
        #     ↓
        # Student Identity Resolver
        #     ↓
        # ResultStore
        # ----------------------------------------------------

        lifecycle_results = (
            evaluation_service.evaluate_and_save_form(
                form_id="integration-test-form",
                assessment_id=10,
                school_id="TCO_TEST",
                class_level="TCO Test Class",
                section="TEST",
            )
        )

        # ----------------------------------------------------
        # Validate response count
        # ----------------------------------------------------

        assert len(
            lifecycle_results
        ) == 1

        lifecycle = (
            lifecycle_results[0]
        )

        print("\nLIFECYCLE RESULT")
        print("-" * 60)

        print(
            "Status:",
            lifecycle["status"],
        )

        print(
            "Response ID:",
            lifecycle["response_id"],
        )

        print(
            "Identity Method:",
            lifecycle["identity_method"],
        )

        # ----------------------------------------------------
        # Evaluation result
        # ----------------------------------------------------

        evaluation = (
            lifecycle[
                "evaluation_result"
            ]
        )

        print("\nEVALUATION")
        print("-" * 60)

        print(
            "Student Name:",
            evaluation["student_name"],
        )

        print(
            "Student ID:",
            evaluation["student_identifier"],
        )

        print(
            "Student Email:",
            evaluation["student_email"],
        )

        print(
            "Identity Status:",
            evaluation["identity_status"],
        )

        print(
            "Obtained:",
            evaluation["obtained_marks"],
        )

        print(
            "Total:",
            evaluation["total_marks"],
        )

        print(
            "Percentage:",
            evaluation["percentage"],
        )

        print(
            "Correct:",
            evaluation["correct_answers"],
        )

        print(
            "Wrong:",
            evaluation["wrong_answers"],
        )

        print(
            "Unanswered:",
            evaluation["unanswered"],
        )

        # ----------------------------------------------------
        # Verify all three identity values
        # ----------------------------------------------------

        assert (
            evaluation["student_name"]
            == student["name"]
        )

        assert (
            evaluation["student_identifier"]
            == student["student_no"]
        )

        assert (
            evaluation["student_email"]
            == student["email"]
        )

        assert (
            evaluation["identity_status"]
            == "captured"
        )

        # ----------------------------------------------------
        # Student ID identity field must be the
        # primary identity field.
        # ----------------------------------------------------

        assert (
            evaluation["identity_field"]["question_id"]
            == "identity-question"
        )

        assert (
            evaluation["identity_field"]["identity_type"]
            == "student_id_or_roll_number"
        )

        # ----------------------------------------------------
        # Verify identity answers never become
        # assessment answers.
        # ----------------------------------------------------

        assessment_answer_ids = {
            answer["question_id"]
            for answer in evaluation["answers"]
        }

        assert assessment_answer_ids == {
            "q1",
            "q2",
        }

        assert (
            "name-question"
            not in assessment_answer_ids
        )

        assert (
            "identity-question"
            not in assessment_answer_ids
        )

        assert (
            "email-question"
            not in assessment_answer_ids
        )

        # ----------------------------------------------------
        # Saved ResultStore result
        # ----------------------------------------------------

        saved = (
            lifecycle[
                "saved_result"
            ]
        )

        print("\nRESULTSTORE")
        print("-" * 60)

        print(
            "Result ID:",
            saved["result_id"],
        )

        print(
            "Assessment ID:",
            saved["assessment_id"],
        )

        print(
            "Student ID:",
            saved["student_id"],
        )

        print(
            "Student Name:",
            saved["student_name"],
        )

        print(
            "Student Email:",
            saved["student_email"],
        )

        print(
            "Obtained:",
            saved["obtained_marks"],
        )

        print(
            "Total:",
            saved["total_marks"],
        )

        print(
            "Percentage:",
            saved["percentage"],
        )

        print(
            "Correct:",
            saved["correct_answers"],
        )

        print(
            "Wrong:",
            saved["wrong_answers"],
        )

        print(
            "Unanswered:",
            saved["unanswered"],
        )

        print(
            "Status:",
            saved["result_status"],
        )

        print(
            "Response ID:",
            saved["form_response_id"],
        )

        # ----------------------------------------------------
        # Verify lifecycle save
        # ----------------------------------------------------

        assert (
            lifecycle["status"]
            == "saved"
        )

        assert (
            lifecycle["identity_method"]
            == "student_no"
        )

        assert (
            saved["student_id"]
            == student["id"]
        )

        assert (
            saved["assessment_id"]
            == 10
        )

        assert (
            saved["student_name"]
            == student["name"]
        )

        assert (
            saved["student_email"]
            == student["email"]
        )

        assert (
            float(
                saved["total_marks"]
            )
            == 5.0
        )

        assert (
            float(
                saved["obtained_marks"]
            )
            == 2.5
        )

        assert (
            float(
                saved["percentage"]
            )
            == 50.0
        )

        assert (
            saved["correct_answers"]
            == 1
        )

        assert (
            saved["wrong_answers"]
            == 1
        )

        assert (
            saved["unanswered"]
            == 0
        )

        assert (
            saved["result_status"]
            == "evaluated"
        )

        assert (
            saved["form_response_id"]
            == "INTEGRATION_RESPONSE_001"
        )

        # ----------------------------------------------------
        # Stored JSON
        # ----------------------------------------------------

        assert saved[
            "answers_json"
        ] is not None

        assert saved[
            "question_results_json"
        ] is not None

        print("\nJSON STORAGE")
        print("-" * 60)

        print(
            "answers_json:",
            "Present",
        )

        print(
            "question_results_json:",
            "Present",
        )

        # ----------------------------------------------------
        # ResultStore read-back
        # ----------------------------------------------------

        loaded = result_store.get_result(
            result_id=int(
                saved["result_id"]
            )
        )

        assert loaded is not None

        assert (
            loaded["student_id"]
            == student["id"]
        )

        assert (
            loaded["assessment_id"]
            == 10
        )

        assert (
            loaded["student_name"]
            == student["name"]
        )

        assert (
            loaded["student_email"]
            == student["email"]
        )

        assert (
            float(
                loaded["percentage"]
            )
            == 50.0
        )

        assert (
            loaded["form_response_id"]
            == "INTEGRATION_RESPONSE_001"
        )

        print("\nREAD-BACK CHECK")
        print("-" * 60)

        print(
            "Result successfully read "
            "from student_result_view."
        )

        print(
            "Result ID:",
            loaded["result_id"],
        )

        print(
            "Student:",
            loaded["student_name"],
        )

        print(
            "Email:",
            loaded["student_email"],
        )

        print(
            "Percentage:",
            loaded["percentage"],
        )

        # ----------------------------------------------------
        # Final success
        # ----------------------------------------------------

        print("\n" + "=" * 60)
        print(
            "TCO 3-FIELD IDENTITY -> RESULTSTORE TEST PASSED"
        )
        print("=" * 60)

        return 0

    finally:
        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )