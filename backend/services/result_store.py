from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "tco.db"
)


class ResultStoreError(RuntimeError):
    """Raised when a student-result database operation fails."""


class ResultStore:
    """
    Persistence layer for assessment attempts/results.

    This class does not contain agent logic.
    It only validates data and reads/writes SQLite.

    Intended usage:
        Assessment workflow -> Database Tool -> ResultStore
        Result/Analytics Agent -> Database Tool -> ResultStore
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path or DEFAULT_DB_PATH).resolve()

        if not self.db_path.exists():
            raise ResultStoreError(
                f"Database file does not exist: {self.db_path}"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return dict(row)

    def save_result(
        self,
        *,
        assessment_id: int,
        student_id: int,
        obtained_marks: float,
        total_marks: float,
        correct_answers: int = 0,
        wrong_answers: int = 0,
        unanswered: int = 0,
        submitted_at: str | None = None,
        started_at: str | None = None,
        form_response_id: str | None = None,
        answers_json: str | None = None,
        question_results_json: str | None = None,
        status: str = "evaluated",
        attempt_number: int = 1,
    ) -> dict[str, Any]:
        """Insert or update one student's result for one assessment attempt."""

        if assessment_id <= 0:
            raise ResultStoreError("assessment_id must be greater than 0.")

        if student_id <= 0:
            raise ResultStoreError("student_id must be greater than 0.")

        if attempt_number <= 0:
            raise ResultStoreError("attempt_number must be greater than 0.")

        if total_marks < 0:
            raise ResultStoreError("total_marks cannot be negative.")

        if obtained_marks < 0:
            raise ResultStoreError("obtained_marks cannot be negative.")

        if total_marks > 0 and obtained_marks > total_marks:
            raise ResultStoreError(
                "obtained_marks cannot be greater than total_marks."
            )

        if correct_answers < 0 or wrong_answers < 0 or unanswered < 0:
            raise ResultStoreError("Answer counts cannot be negative.")

        percentage = (
            round((obtained_marks / total_marks) * 100, 2)
            if total_marks
            else 0.0
        )

        now = self._utc_now()
        submitted_at = submitted_at or now

        with self._connect() as connection:
            student = connection.execute(
                """
                SELECT
                    id,
                    name,
                    email,
                    student_no,
                    university_roll,
                    class_level,
                    section,
                    school_id
                FROM students
                WHERE id = ?
                """,
                (student_id,),
            ).fetchone()

            if student is None:
                raise ResultStoreError(
                    f"Student not found: student_id={student_id}"
                )

            assessment = connection.execute(
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
                    test_date,
                    school_id,
                    form_id
                FROM assessments
                WHERE id = ?
                """,
                (assessment_id,),
            ).fetchone()

            if assessment is None:
                raise ResultStoreError(
                    f"Assessment not found: assessment_id={assessment_id}"
                )

            if assessment["school_id"] and student["school_id"]:
                if str(assessment["school_id"]) != str(student["school_id"]):
                    raise ResultStoreError(
                        "Assessment and student belong to different schools."
                    )

            cursor = connection.execute(
                """
                INSERT INTO assessment_attempts (
                    assessment_id,
                    student_id,
                    attempt_number,
                    student_name,
                    student_email,
                    started_at,
                    submitted_at,
                    obtained_marks,
                    total_marks,
                    percentage,
                    correct_answers,
                    wrong_answers,
                    unanswered,
                    status,
                    form_response_id,
                    answers_json,
                    question_results_json,
                    result_email_status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'not_sent', ?, ?)
                ON CONFLICT (assessment_id, student_id, attempt_number)
                DO UPDATE SET
                    student_name = excluded.student_name,
                    student_email = excluded.student_email,
                    started_at = excluded.started_at,
                    submitted_at = excluded.submitted_at,
                    obtained_marks = excluded.obtained_marks,
                    total_marks = excluded.total_marks,
                    percentage = excluded.percentage,
                    correct_answers = excluded.correct_answers,
                    wrong_answers = excluded.wrong_answers,
                    unanswered = excluded.unanswered,
                    status = excluded.status,
                    form_response_id = excluded.form_response_id,
                    answers_json = excluded.answers_json,
                    question_results_json = excluded.question_results_json,
                    updated_at = excluded.updated_at
                """,
                (
                    assessment_id,
                    student_id,
                    attempt_number,
                    student["name"],
                    student["email"],
                    started_at,
                    submitted_at,
                    float(obtained_marks),
                    float(total_marks),
                    percentage,
                    int(correct_answers),
                    int(wrong_answers),
                    int(unanswered),
                    status,
                    form_response_id,
                    answers_json,
                    question_results_json,
                    now,
                    now,
                ),
            )

            result_id = cursor.lastrowid

            # ON CONFLICT UPDATE may not provide the existing row id.
            if not result_id:
                result_row = connection.execute(
                    """
                    SELECT id
                    FROM assessment_attempts
                    WHERE assessment_id = ?
                      AND student_id = ?
                      AND attempt_number = ?
                    """,
                    (
                        assessment_id,
                        student_id,
                        attempt_number,
                    ),
                ).fetchone()

                if result_row is None:
                    raise ResultStoreError(
                        "Result was not saved and could not be reloaded."
                    )

                result_id = int(result_row["id"])

            result_row = connection.execute(
                """
                SELECT *
                FROM student_result_view
                WHERE result_id = ?
                """,
                (result_id,),
            ).fetchone()

            saved = self._row_to_dict(result_row)

            if saved is None:
                raise ResultStoreError(
                    f"Saved result could not be read back: result_id={result_id}"
                )

            return saved

    def get_result(
        self,
        *,
        result_id: int,
    ) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM student_result_view
                WHERE result_id = ?
                """,
                (result_id,),
            ).fetchone()

            return self._row_to_dict(row)

    def get_student_results(
        self,
        *,
        student_name: str | None = None,
        student_id: int | None = None,
        student_email: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Return a student's result history.

        Matching is case-insensitive.
        Prefer student_id/email when available.
        """

        if limit <= 0:
            raise ResultStoreError("limit must be greater than 0.")

        conditions: list[str] = []
        parameters: list[Any] = []

        if student_id is not None:
            conditions.append("student_id = ?")
            parameters.append(student_id)

        if student_email:
            conditions.append("LOWER(student_email) = LOWER(?)")
            parameters.append(student_email.strip())

        if student_name:
            conditions.append("LOWER(student_name) = LOWER(?)")
            parameters.append(student_name.strip())

        if not conditions:
            raise ResultStoreError(
                "Provide student_id, student_email, or student_name."
            )

        query = f"""
            SELECT *
            FROM student_result_view
            WHERE {" OR ".join(conditions)}
            ORDER BY test_date DESC, submitted_at DESC, result_id DESC
            LIMIT ?
        """

        parameters.append(int(limit))

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
            return [dict(row) for row in rows]

    def query_results(
        self,
        *,
        student_name: str | None = None,
        topic: str | None = None,
        subject: str | None = None,
        class_level: str | None = None,
        section: str | None = None,
        school_id: str | None = None,
        min_marks: float | None = None,
        max_marks: float | None = None,
        min_percentage: float | None = None,
        max_percentage: float | None = None,
        test_date_from: str | None = None,
        test_date_to: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Flexible structured query for the future Result/Analytics Agent.

        Examples:
            max_marks=10
            max_percentage=40
            topic="Booth Algorithm"
            student_name="Rahul"
            test_date_from="2026-10-01"
            test_date_to="2026-10-05"
        """

        if limit <= 0:
            raise ResultStoreError("limit must be greater than 0.")

        conditions: list[str] = []
        parameters: list[Any] = []

        if student_name:
            conditions.append("LOWER(student_name) LIKE LOWER(?)")
            parameters.append(f"%{student_name.strip()}%")

        if topic:
            conditions.append("LOWER(topic) LIKE LOWER(?)")
            parameters.append(f"%{topic.strip()}%")

        if subject:
            conditions.append("LOWER(subject) LIKE LOWER(?)")
            parameters.append(f"%{subject.strip()}%")

        if class_level:
            conditions.append(
                "LOWER(assessment_class_level) = LOWER(?)"
            )
            parameters.append(class_level.strip())

        if section:
            conditions.append(
                "LOWER(assessment_section) = LOWER(?)"
            )
            parameters.append(section.strip())

        if school_id:
            conditions.append("student_school_id = ?")
            parameters.append(school_id)

        if min_marks is not None:
            conditions.append("obtained_marks >= ?")
            parameters.append(float(min_marks))

        if max_marks is not None:
            conditions.append("obtained_marks <= ?")
            parameters.append(float(max_marks))

        if min_percentage is not None:
            conditions.append("percentage >= ?")
            parameters.append(float(min_percentage))

        if max_percentage is not None:
            conditions.append("percentage <= ?")
            parameters.append(float(max_percentage))

        if test_date_from:
            conditions.append("test_date >= ?")
            parameters.append(test_date_from)

        if test_date_to:
            conditions.append("test_date <= ?")
            parameters.append(test_date_to)

        if status:
            conditions.append("result_status = ?")
            parameters.append(status.strip())

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT *
            FROM student_result_view
            {where_clause}
            ORDER BY test_date DESC, submitted_at DESC, result_id DESC
            LIMIT ?
        """

        parameters.append(int(limit))

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
            return [dict(row) for row in rows]

    def update_result_email_status(
        self,
        *,
        result_id: int,
        status: str,
        error: str | None = None,
        sent_at: str | None = None,
    ) -> dict[str, Any]:
        """
        Track result-email delivery independently from the result itself.

        status examples:
            not_sent
            sent
            failed
        """

        allowed_statuses = {
            "not_sent",
            "sent",
            "failed",
            "skipped",
        }

        if status not in allowed_statuses:
            raise ResultStoreError(
                f"Invalid result email status: {status}"
            )

        if status == "sent":
            sent_at = sent_at or self._utc_now()
        elif status != "sent":
            sent_at = None

        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE assessment_attempts
                SET
                    result_email_status = ?,
                    result_email_sent_at = ?,
                    result_email_error = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    sent_at,
                    error,
                    self._utc_now(),
                    result_id,
                ),
            )

            if cursor.rowcount == 0:
                raise ResultStoreError(
                    f"Result not found: result_id={result_id}"
                )

            row = connection.execute(
                """
                SELECT *
                FROM student_result_view
                WHERE result_id = ?
                """,
                (result_id,),
            ).fetchone()

            updated = self._row_to_dict(row)

            if updated is None:
                raise ResultStoreError(
                    f"Updated result could not be read back: result_id={result_id}"
                )

            return updated

    def get_pending_result_emails(
        self,
        *,
        assessment_id: int | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        if limit <= 0:
            raise ResultStoreError("limit must be greater than 0.")

        parameters: list[Any] = []
        where = ["result_email_status = 'not_sent'"]

        if assessment_id is not None:
            where.append("assessment_id = ?")
            parameters.append(assessment_id)

        parameters.append(limit)

        query = f"""
            SELECT *
            FROM student_result_view
            WHERE {" AND ".join(where)}
            ORDER BY submitted_at ASC, result_id ASC
            LIMIT ?
        """

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
            return [dict(row) for row in rows]


__all__ = [
    "ResultStore",
    "ResultStoreError",
]
