from __future__ import annotations

import shutil
import sqlite3
import tempfile
from pathlib import Path

from backend.services.assessment_result_service import (
    AssessmentResultService,
)


PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
)

SOURCE_DB = (
    PROJECT_ROOT
    / "data"
    / "tco.db"
)


def find_test_student(
    db_path: Path,
) -> dict:
    connection = sqlite3.connect(
        db_path
    )
    connection.row_factory = (
        sqlite3.Row
    )

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


def find_test_assessment(
    db_path: Path,
) -> dict:
    connection = sqlite3.connect(
        db_path
    )
    connection.row_factory = (
        sqlite3.Row
    )

    try:
        row = connection.execute(
            """
            SELECT
                id,
                title,
                subject,
                chapter,
                topic,
                class_level,
                section,
                total_marks,
                school_id,
                form_id
            FROM assessments
            WHERE id = ?
            LIMIT 1
            """,
            (10,),
        ).fetchone()

        if row is None:
            raise RuntimeError(
                "Expected test assessment_id=10 was not found."
            )

        return dict(row)

    finally:
        connection.close()


def main() -> None:
    print("=" * 60)
    print("TCO ASSESSMENT RESULT SERVICE TEST")
    print("=" * 60)

    if not SOURCE_DB.exists():
        raise RuntimeError(
            f"Database not found: {SOURCE_DB}"
        )

    # --------------------------------------------------------
    # Create temporary database copy.
    # --------------------------------------------------------

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix="tco_result_test_"
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

    print("Source DB:", SOURCE_DB)
    print("Test DB:  ", test_db)

    try:
        # ----------------------------------------------------
        # Load known test records.
        # ----------------------------------------------------

        student = find_test_student(
            test_db
        )

        assessment = find_test_assessment(
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

        print("\nTEST ASSESSMENT")
        print("-" * 60)
        print(
            "Assessment ID:",
            assessment["id"],
        )
        print(
            "Title:",
            assessment["title"],
        )
        print(
            "Topic:",
            assessment["topic"],
        )
        print(
            "Total Marks:",
            assessment["total_marks"],
        )

        # ----------------------------------------------------
        # Fake output from Evaluation Agent.
        #
        # This is intentionally structured exactly like the
        # current evaluation contract.
        # ----------------------------------------------------

        evaluation_result = {
            "submission_source": "google_forms",
            "submission_id": (
                "TEST_RESPONSE_001"
            ),
            "student_id": None,
            "student_name": student[
                "name"
            ],
            "student_email": student[
                "email"
            ],
            "submitted_at": (
                "2026-10-05T10:30:00+00:00"
            ),
            "obtained_marks": 12.0,
            "total_marks": 20.0,
            "percentage": 60.0,
            "correct_answers": 3,
            "wrong_answers": 2,
            "unanswered": 0,
            "review_required": False,
            "evaluation_status": "complete",
            "question_results": [
                {
                    "question_id": "q1",
                    "status": "correct",
                    "marks_awarded": 4.0,
                    "max_marks": 4.0,
                    "student_answer": "A",
                },
                {
                    "question_id": "q2",
                    "status": "wrong",
                    "marks_awarded": 0.0,
                    "max_marks": 4.0,
                    "student_answer": "B",
                },
                {
                    "question_id": "q3",
                    "status": "correct",
                    "marks_awarded": 4.0,
                    "max_marks": 4.0,
                    "student_answer": "C",
                },
                {
                    "question_id": "q4",
                    "status": "correct",
                    "marks_awarded": 4.0,
                    "max_marks": 4.0,
                    "student_answer": "A",
                },
                {
                    "question_id": "q5",
                    "status": "wrong",
                    "marks_awarded": 0.0,
                    "max_marks": 4.0,
                    "student_answer": "D",
                },
            ],
        }

        # ----------------------------------------------------
        # Create services against temporary DB.
        # ----------------------------------------------------

        from backend.services.result_store import (
            ResultStore,
        )
        from backend.services.student_identity import (
            StudentIdentityResolver,
        )

        result_store = ResultStore(
            db_path=test_db
        )

        identity_resolver = (
            StudentIdentityResolver(
                db_path=test_db
            )
        )

        service = (
            AssessmentResultService(
                result_store=result_store,
                identity_resolver=identity_resolver,
            )
        )

        # ----------------------------------------------------
        # Save evaluated result.
        # ----------------------------------------------------

        result = (
            service.save_evaluated_result(
                assessment_id=int(
                    assessment["id"]
                ),
                evaluation_result=(
                    evaluation_result
                ),
                school_id=student[
                    "school_id"
                ],
                class_level=student[
                    "class_level"
                ],
                section=student[
                    "section"
                ],
                attempt_number=1,
            )
        )

        print("\nIDENTITY RESOLUTION")
        print("-" * 60)
        print(
            "Method:",
            result[
                "identity_method"
            ],
        )

        resolved_student = (
            result["student"]
        )

        print(
            "Student ID:",
            resolved_student[
                "student_id"
            ],
        )
        print(
            "Student Name:",
            resolved_student[
                "name"
            ],
        )

        # ----------------------------------------------------
        # Saved database result.
        # ----------------------------------------------------

        saved = result[
            "saved_result"
        ]

        print("\nSAVED RESULT")
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
            "Obtained Marks:",
            saved["obtained_marks"],
        )
        print(
            "Total Marks:",
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
        # Assertions.
        # ----------------------------------------------------

        assert result["status"] == "saved"

        assert (
            result["identity_method"]
            == "email"
        )

        assert (
            saved["student_id"]
            == student["id"]
        )

        assert (
            saved["assessment_id"]
            == assessment["id"]
        )

        assert (
            float(
                saved["obtained_marks"]
            )
            == 12.0
        )

        assert (
            float(
                saved["total_marks"]
            )
            == 20.0
        )

        assert (
            float(
                saved["percentage"]
            )
            == 60.0
        )

        assert (
            saved["correct_answers"]
            == 3
        )

        assert (
            saved["wrong_answers"]
            == 2
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
            == "TEST_RESPONSE_001"
        )

        # ----------------------------------------------------
        # Verify question results were persisted.
        # ----------------------------------------------------

        raw_question_results = (
            saved["question_results_json"]
        )

        assert raw_question_results

        print("\nQUESTION RESULTS")
        print("-" * 60)
        print(
            "Stored:",
            "question_results_json"
            in saved,
        )

        # ----------------------------------------------------
        # Final.
        # ----------------------------------------------------

        print("\n" + "=" * 60)
        print(
            "ASSESSMENT RESULT SERVICE TEST PASSED"
        )
        print("=" * 60)

    finally:
        # ----------------------------------------------------
        # Remove temporary DB.
        # Original tco.db remains untouched.
        # ----------------------------------------------------

        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )


if __name__ == "__main__":
    main()