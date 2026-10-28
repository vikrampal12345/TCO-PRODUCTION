from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.core.base_tool import BaseTool
from backend.core.tool_result import ToolResult


class DatabaseTool(BaseTool):
    """
    SQLite database tool for TCO.

    Responsibilities:
    - Store student records
    - Store assessments
    - Store assessment questions
    - Store student test attempts
    - Store individual responses
    - Fetch student information
    - Fetch student emails
    - Fetch student results

    This tool performs deterministic database operations.
    It does NOT make business decisions.
    """

    name = "database"

    description = (
        "Stores and retrieves TCO student, assessment, "
        "submission and result data using SQLite."
    )

    capabilities = (
        "db.student.create",
        "db.student.get",
        "db.student.list",
        "db.student.update",
        "db.student.get_emails",
        "db.assessment.save",
        "db.assessment.get",
        "db.attempt.save",
        "db.attempt.get",
        "db.student.results",
    )

    def __init__(
        self,
        database_path: str | Path | None = None,
    ) -> None:

        self.project_root = Path(__file__).resolve().parents[2]

        if database_path is None:
            database_path = (
                self.project_root
                / "data"
                / "tco.db"
            )

        self.database_path = Path(database_path)

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.initialize_database()

    # =========================================================
    # CONNECTION
    # =========================================================

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path,
        )

        connection.row_factory = sqlite3.Row

        # Foreign keys must be explicitly enabled in SQLite.
        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        return connection

    # =========================================================
    # DATABASE INITIALIZATION
    # =========================================================

    def initialize_database(self) -> None:

        with self._connect() as connection:

            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    student_no TEXT NOT NULL UNIQUE,
                    university_roll TEXT UNIQUE,

                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    phone TEXT,

                    address TEXT,

                    class_level TEXT,
                    section TEXT,
                    course TEXT,
                    semester TEXT,

                    school_id TEXT,

                    parent_name TEXT,
                    parent_email TEXT,
                    parent_phone TEXT,

                    is_active INTEGER NOT NULL DEFAULT 1,

                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS assessments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    title TEXT NOT NULL,

                    subject TEXT,
                    chapter TEXT,
                    topic TEXT,

                    class_level TEXT,
                    section TEXT,

                    total_marks INTEGER NOT NULL,
                    question_count INTEGER NOT NULL,

                    generation_mode TEXT,

                    form_id TEXT,
                    responder_url TEXT,

                    status TEXT NOT NULL DEFAULT 'draft',

                    created_by TEXT,
                    school_id TEXT,

                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS assessment_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    assessment_id INTEGER NOT NULL,

                    question_number INTEGER NOT NULL,
                    question_text TEXT NOT NULL,

                    options_json TEXT NOT NULL,

                    correct_option INTEGER NOT NULL,
                    marks INTEGER NOT NULL DEFAULT 1,

                    FOREIGN KEY (
                        assessment_id
                    )
                    REFERENCES assessments(id)
                    ON DELETE CASCADE,

                    UNIQUE(
                        assessment_id,
                        question_number
                    )
                );

                CREATE TABLE IF NOT EXISTS test_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    assessment_id INTEGER NOT NULL,
                    student_id INTEGER NOT NULL,

                    score REAL NOT NULL DEFAULT 0,
                    max_score REAL NOT NULL DEFAULT 0,

                    status TEXT NOT NULL DEFAULT 'started',

                    started_at TEXT NOT NULL,
                    submitted_at TEXT,

                    FOREIGN KEY (
                        assessment_id
                    )
                    REFERENCES assessments(id)
                    ON DELETE CASCADE,

                    FOREIGN KEY (
                        student_id
                    )
                    REFERENCES students(id)
                    ON DELETE CASCADE,

                    UNIQUE(
                        assessment_id,
                        student_id
                    )
                );

                CREATE TABLE IF NOT EXISTS responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    attempt_id INTEGER NOT NULL,
                    question_id INTEGER NOT NULL,

                    selected_option INTEGER,

                    is_correct INTEGER NOT NULL DEFAULT 0,

                    marks_awarded REAL NOT NULL DEFAULT 0,

                    answered_at TEXT,

                    FOREIGN KEY (
                        attempt_id
                    )
                    REFERENCES test_attempts(id)
                    ON DELETE CASCADE,

                    FOREIGN KEY (
                        question_id
                    )
                    REFERENCES assessment_questions(id)
                    ON DELETE CASCADE,

                    UNIQUE(
                        attempt_id,
                        question_id
                    )
                );

                CREATE INDEX IF NOT EXISTS
                idx_students_school
                ON students(school_id);

                CREATE INDEX IF NOT EXISTS
                idx_attempts_student
                ON test_attempts(student_id);

                CREATE INDEX IF NOT EXISTS
                idx_attempts_assessment
                ON test_attempts(assessment_id);

                CREATE INDEX IF NOT EXISTS
                idx_questions_assessment
                ON assessment_questions(assessment_id);
                """
            )

    # =========================================================
    # UTILITY
    # =========================================================

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().isoformat()

    @staticmethod
    def _row_to_dict(
        row: sqlite3.Row | None,
    ) -> dict[str, Any] | None:

        if row is None:
            return None

        return dict(row)

    # =========================================================
    # STUDENT CREATE
    # =========================================================

    def create_student(
        self,
        *,
        student_no: str,
        name: str,
        email: str,
        phone: str = "",
        university_roll: str = "",
        address: str = "",
        class_level: str = "",
        section: str = "",
        course: str = "",
        semester: str = "",
        school_id: str = "",
        parent_name: str = "",
        parent_email: str = "",
        parent_phone: str = "",
    ) -> ToolResult:

        student_no = student_no.strip()
        name = name.strip()
        email = email.strip().lower()

        if not student_no:
            return ToolResult.failure(
                "INVALID_STUDENT_NO",
                "student_no is required.",
            )

        if not name:
            return ToolResult.failure(
                "INVALID_NAME",
                "Student name is required.",
            )

        if not email:
            return ToolResult.failure(
                "INVALID_EMAIL",
                "Student email is required.",
            )

        now = self._now()

        try:

            with self._connect() as connection:

                cursor = connection.execute(
                    """
                    INSERT INTO students (
                        student_no,
                        university_roll,
                        name,
                        email,
                        phone,
                        address,
                        class_level,
                        section,
                        course,
                        semester,
                        school_id,
                        parent_name,
                        parent_email,
                        parent_phone,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        student_no,
                        university_roll.strip() or None,
                        name,
                        email,
                        phone.strip(),
                        address.strip(),
                        class_level.strip(),
                        section.strip(),
                        course.strip(),
                        semester.strip(),
                        school_id.strip(),
                        parent_name.strip(),
                        parent_email.strip(),
                        parent_phone.strip(),
                        now,
                        now,
                    ),
                )

                student_id = cursor.lastrowid

                row = connection.execute(
                    """
                    SELECT *
                    FROM students
                    WHERE id = ?
                    """,
                    (student_id,),
                ).fetchone()

            return ToolResult.ok(
                data=self._row_to_dict(row),
            )

        except sqlite3.IntegrityError as exc:

            return ToolResult.failure(
                "STUDENT_ALREADY_EXISTS",
                str(exc),
            )

    # =========================================================
    # GET STUDENT
    # =========================================================

    def get_student(
        self,
        *,
        student_id: int | None = None,
        student_no: str | None = None,
        university_roll: str | None = None,
        email: str | None = None,
    ) -> ToolResult:

        if not any(
            [
                student_id is not None,
                student_no,
                university_roll,
                email,
            ]
        ):
            return ToolResult.failure(
                "MISSING_LOOKUP",
                "Provide student_id, student_no, "
                "university_roll or email.",
            )

        conditions = []
        values = []

        if student_id is not None:
            conditions.append("id = ?")
            values.append(student_id)

        elif student_no:
            conditions.append("student_no = ?")
            values.append(student_no.strip())

        elif university_roll:
            conditions.append("university_roll = ?")
            values.append(university_roll.strip())

        elif email:
            conditions.append("email = ?")
            values.append(email.strip().lower())

        with self._connect() as connection:

            row = connection.execute(
                f"""
                SELECT *
                FROM students
                WHERE {" AND ".join(conditions)}
                LIMIT 1
                """,
                values,
            ).fetchone()

        if row is None:
            return ToolResult.failure(
                "STUDENT_NOT_FOUND",
                "Student record not found.",
            )

        return ToolResult.ok(
            data=self._row_to_dict(row),
        )

    # =========================================================
    # LIST STUDENTS
    # =========================================================

    def list_students(
        self,
        *,
        school_id: str | None = None,
        class_level: str | None = None,
        section: str | None = None,
    ) -> ToolResult:

        conditions = ["is_active = 1"]
        values = []

        if school_id:
            conditions.append("school_id = ?")
            values.append(school_id.strip())

        if class_level:
            conditions.append("class_level = ?")
            values.append(class_level.strip())

        if section:
            conditions.append("section = ?")
            values.append(section.strip())

        with self._connect() as connection:

            rows = connection.execute(
                f"""
                SELECT *
                FROM students
                WHERE {" AND ".join(conditions)}
                ORDER BY name
                """,
                values,
            ).fetchall()

        return ToolResult.ok(
            data=[
                dict(row)
                for row in rows
            ],
        )

    # =========================================================
    # UPDATE STUDENT
    # =========================================================

    def update_student(
        self,
        *,
        student_id: int,
        **fields: Any,
    ) -> ToolResult:

        allowed_fields = {
            "student_no",
            "university_roll",
            "name",
            "email",
            "phone",
            "address",
            "class_level",
            "section",
            "course",
            "semester",
            "school_id",
            "parent_name",
            "parent_email",
            "parent_phone",
            "is_active",
        }

        updates = []

        values = []

        for field_name, value in fields.items():

            if field_name not in allowed_fields:
                continue

            if field_name in {
                "email",
                "parent_email",
            } and isinstance(value, str):

                value = value.strip().lower()

            updates.append(
                f"{field_name} = ?"
            )

            values.append(value)

        if not updates:
            return ToolResult.failure(
                "NO_FIELDS",
                "No valid fields supplied for update.",
            )

        updates.append(
            "updated_at = ?"
        )

        values.append(
            self._now()
        )

        values.append(
            student_id
        )

        try:

            with self._connect() as connection:

                connection.execute(
                    f"""
                    UPDATE students
                    SET {", ".join(updates)}
                    WHERE id = ?
                    """,
                    values,
                )

                row = connection.execute(
                    """
                    SELECT *
                    FROM students
                    WHERE id = ?
                    """,
                    (student_id,),
                ).fetchone()

            if row is None:
                return ToolResult.failure(
                    "STUDENT_NOT_FOUND",
                    "Student record not found.",
                )

            return ToolResult.ok(
                data=self._row_to_dict(row),
            )

        except sqlite3.IntegrityError as exc:

            return ToolResult.failure(
                "STUDENT_UPDATE_FAILED",
                str(exc),
            )

    # =========================================================
    # GET STUDENT EMAILS
    # =========================================================

    def get_student_emails(
        self,
        *,
        school_id: str | None = None,
        class_level: str | None = None,
        section: str | None = None,
    ) -> ToolResult:

        result = self.list_students(
            school_id=school_id,
            class_level=class_level,
            section=section,
        )

        if not result.success:
            return result

        students = result.data or []

        def _is_valid_email_for_delivery(value):
            address = str(value or '').strip()
            if address.count('@') != 1 or any(c.isspace() for c in address):
                return False
            local, domain = address.split('@', 1)
            return bool(local and '.' in domain and not domain.startswith('.') and not domain.endswith('.'))

        emails = [
            str(student.get('email') or '').strip()
            for student in students
            if _is_valid_email_for_delivery(student.get('email'))
        ]

        return ToolResult.ok(
            data=emails,
        )

    # =========================================================
    # CREATE ASSESSMENT
    # =========================================================

    def create_assessment(
        self,
        *,
        title: str,
        questions: list[dict[str, Any]],
        subject: str = "",
        chapter: str = "",
        topic: str = "",
        class_level: str = "",
        section: str = "",
        total_marks: int = 0,
        generation_mode: str = "",
        form_id: str = "",
        responder_url: str = "",
        status: str = "draft",
        created_by: str = "",
        school_id: str = "",
    ) -> ToolResult:

        if not title.strip():
            return ToolResult.failure(
                "INVALID_ASSESSMENT_TITLE",
                "Assessment title is required.",
            )

        if not questions:
            return ToolResult.failure(
                "NO_QUESTIONS",
                "Assessment must contain questions.",
            )

        question_count = len(questions)

        if total_marks <= 0:
            total_marks = sum(
                int(question.get("marks", 1))
                for question in questions
            )

        now = self._now()

        with self._connect() as connection:

            cursor = connection.execute(
                """
                INSERT INTO assessments (
                    title,
                    subject,
                    chapter,
                    topic,
                    class_level,
                    section,
                    total_marks,
                    question_count,
                    generation_mode,
                    form_id,
                    responder_url,
                    status,
                    created_by,
                    school_id,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title.strip(),
                    subject.strip(),
                    chapter.strip(),
                    topic.strip(),
                    class_level.strip(),
                    section.strip(),
                    total_marks,
                    question_count,
                    generation_mode.strip(),
                    form_id.strip(),
                    responder_url.strip(),
                    status.strip(),
                    created_by.strip(),
                    school_id.strip(),
                    now,
                    now,
                ),
            )

            assessment_id = cursor.lastrowid

            for index, question in enumerate(
                questions,
                start=1,
            ):

                options = question.get(
                    "options",
                    [],
                )

                connection.execute(
                    """
                    INSERT INTO assessment_questions (
                        assessment_id,
                        question_number,
                        question_text,
                        options_json,
                        correct_option,
                        marks
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        assessment_id,
                        int(
                            question.get(
                                "question_number",
                                index,
                            )
                        ),
                        str(
                            question.get(
                                "question",
                                "",
                            )
                        ).strip(),
                        json.dumps(
                            options,
                            ensure_ascii=False,
                        ),
                        int(
                            question.get(
                                "correct_option",
                                1,
                            )
                        ),
                        int(
                            question.get(
                                "marks",
                                1,
                            )
                        ),
                    ),
                )

        return ToolResult.ok(
            data={
                "assessment_id": assessment_id,
                "question_count": question_count,
                "total_marks": total_marks,
            },
        )

    # =========================================================
    # GET ASSESSMENT
    # =========================================================

    def get_assessment(
        self,
        *,
        assessment_id: int,
    ) -> ToolResult:

        with self._connect() as connection:

            assessment = connection.execute(
                """
                SELECT *
                FROM assessments
                WHERE id = ?
                """,
                (assessment_id,),
            ).fetchone()

            if assessment is None:
                return ToolResult.failure(
                    "ASSESSMENT_NOT_FOUND",
                    "Assessment not found.",
                )

            question_rows = connection.execute(
                """
                SELECT *
                FROM assessment_questions
                WHERE assessment_id = ?
                ORDER BY question_number
                """,
                (assessment_id,),
            ).fetchall()

        assessment_data = dict(
            assessment
        )

        questions = []

        for row in question_rows:

            question = dict(row)

            question["options"] = json.loads(
                question.pop("options_json")
            )

            questions.append(question)

        assessment_data["questions"] = questions

        return ToolResult.ok(
            data=assessment_data,
        )

    # =========================================================
    # CREATE TEST ATTEMPT
    # =========================================================

    def create_attempt(
        self,
        *,
        assessment_id: int,
        student_id: int,
        score: float = 0,
        max_score: float = 0,
        status: str = "submitted",
        started_at: str | None = None,
        submitted_at: str | None = None,
        responses: list[dict[str, Any]] | None = None,
    ) -> ToolResult:

        if started_at is None:
            started_at = self._now()

        if status == "submitted" and submitted_at is None:
            submitted_at = self._now()

        try:

            with self._connect() as connection:

                cursor = connection.execute(
                    """
                    INSERT INTO test_attempts (
                        assessment_id,
                        student_id,
                        score,
                        max_score,
                        status,
                        started_at,
                        submitted_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        assessment_id,
                        student_id,
                        score,
                        max_score,
                        status,
                        started_at,
                        submitted_at,
                    ),
                )

                attempt_id = cursor.lastrowid

                for response in responses or []:

                    connection.execute(
                        """
                        INSERT INTO responses (
                            attempt_id,
                            question_id,
                            selected_option,
                            is_correct,
                            marks_awarded,
                            answered_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            attempt_id,
                            int(
                                response["question_id"]
                            ),
                            response.get(
                                "selected_option"
                            ),
                            int(
                                bool(
                                    response.get(
                                        "is_correct",
                                        False,
                                    )
                                )
                            ),
                            float(
                                response.get(
                                    "marks_awarded",
                                    0,
                                )
                            ),
                            response.get(
                                "answered_at"
                            )
                            or self._now(),
                        ),
                    )

            return ToolResult.ok(
                data={
                    "attempt_id": attempt_id,
                },
            )

        except sqlite3.IntegrityError as exc:

            return ToolResult.failure(
                "ATTEMPT_CREATE_FAILED",
                str(exc),
            )

    # =========================================================
    # GET ATTEMPT
    # =========================================================

    def get_attempt(
        self,
        *,
        attempt_id: int,
    ) -> ToolResult:

        with self._connect() as connection:

            attempt = connection.execute(
                """
                SELECT
                    ta.*,
                    s.name AS student_name,
                    s.email AS student_email,
                    a.title AS assessment_title
                FROM test_attempts ta
                JOIN students s
                    ON s.id = ta.student_id
                JOIN assessments a
                    ON a.id = ta.assessment_id
                WHERE ta.id = ?
                """,
                (attempt_id,),
            ).fetchone()

            if attempt is None:
                return ToolResult.failure(
                    "ATTEMPT_NOT_FOUND",
                    "Test attempt not found.",
                )

            responses = connection.execute(
                """
                SELECT
                    r.*,
                    aq.question_number,
                    aq.question_text
                FROM responses r
                JOIN assessment_questions aq
                    ON aq.id = r.question_id
                WHERE r.attempt_id = ?
                ORDER BY aq.question_number
                """,
                (attempt_id,),
            ).fetchall()

        return ToolResult.ok(
            data={
                "attempt": dict(attempt),
                "responses": [
                    dict(row)
                    for row in responses
                ],
            },
        )

    # =========================================================
    # STUDENT RESULTS
    # =========================================================

    def get_student_results(
        self,
        *,
        student_id: int,
    ) -> ToolResult:

        with self._connect() as connection:

            rows = connection.execute(
                """
                SELECT
                    ta.id AS attempt_id,
                    ta.score,
                    ta.max_score,
                    ta.status,
                    ta.started_at,
                    ta.submitted_at,

                    a.id AS assessment_id,
                    a.title,
                    a.subject,
                    a.chapter,
                    a.topic,

                    CASE
                        WHEN ta.max_score > 0
                        THEN (
                            ta.score * 100.0
                            / ta.max_score
                        )
                        ELSE 0
                    END AS percentage

                FROM test_attempts ta

                JOIN assessments a
                    ON a.id = ta.assessment_id

                WHERE ta.student_id = ?

                ORDER BY
                    ta.submitted_at DESC
                """,
                (student_id,),
            ).fetchall()

        return ToolResult.ok(
            data=[
                dict(row)
                for row in rows
            ],
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
            "db.student.create": self.create_student,
            "db.student.get": self.get_student,
            "db.student.list": self.list_students,
            "db.student.update": self.update_student,
            "db.student.get_emails": self.get_student_emails,
            "db.assessment.save": self.create_assessment,
            "db.assessment.get": self.get_assessment,
            "db.attempt.save": self.create_attempt,
            "db.attempt.get": self.get_attempt,
            "db.student.results": self.get_student_results,
        }

        handler = operations.get(operation)

        if handler is None:
            return ToolResult.failure(
                "UNKNOWN_OPERATION",
                f"Unsupported database operation: {operation}",
            )

        return handler(**kwargs)