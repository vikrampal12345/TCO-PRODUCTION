from __future__ import annotations

import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = PROJECT_ROOT / "data" / "tco.db"


# When copied into E:\TCO\scripts\, this resolves to E:\TCO\data\tco.db.
# When run from another location, pass the DB path as the first CLI argument.


def resolve_db_path() -> Path:
    import sys

    if len(sys.argv) > 1:
        return Path(sys.argv[1]).expanduser().resolve()

    # Default for the current working directory.
    root_default = Path.cwd()

    return root_default / "data" / "tco.db"


# ============================================================
# TABLE HELPERS
# ============================================================


def table_exists(
    connection: sqlite3.Connection,
    table_name: str,
) -> bool:
    row = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def table_columns(
    connection: sqlite3.Connection,
    table_name: str,
) -> set[str]:
    rows = connection.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return {
        row[1]
        for row in rows
    }


# ============================================================
# ASSESSMENT TEST DATE
# ============================================================


def add_test_date_column(
    connection: sqlite3.Connection,
) -> None:
    if not table_exists(
        connection,
        "assessments",
    ):
        raise RuntimeError(
            "The existing 'assessments' table was not found. "
            "Run this migration against the same tco.db used by TCO."
        )

    columns = table_columns(
        connection,
        "assessments",
    )

    if "test_date" not in columns:
        connection.execute(
            """
            ALTER TABLE assessments
            ADD COLUMN test_date TEXT
            """
        )

        print(
            "Added assessments.test_date"
        )

    else:
        print(
            "assessments.test_date already exists"
        )

    # Existing assessments get a sensible test date
    # from created_at where possible.

    columns = table_columns(
        connection,
        "assessments",
    )

    if "created_at" in columns:
        connection.execute(
            """
            UPDATE assessments
            SET test_date = substr(created_at, 1, 10)
            WHERE (test_date IS NULL OR trim(test_date) = '')
              AND created_at IS NOT NULL
            """
        )

        print(
            "Backfilled assessments.test_date "
            "from created_at where possible"
        )


# ============================================================
# RESULT TABLE
# ============================================================


def create_result_table(
    connection: sqlite3.Connection,
) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS assessment_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            assessment_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            attempt_number INTEGER NOT NULL DEFAULT 1,

            student_name TEXT,
            student_email TEXT,

            started_at TEXT,
            submitted_at TEXT,

            obtained_marks REAL NOT NULL DEFAULT 0,
            total_marks REAL NOT NULL DEFAULT 0,
            percentage REAL NOT NULL DEFAULT 0,

            correct_answers INTEGER NOT NULL DEFAULT 0,
            wrong_answers INTEGER NOT NULL DEFAULT 0,
            unanswered INTEGER NOT NULL DEFAULT 0,

            status TEXT NOT NULL DEFAULT 'submitted',
            form_response_id TEXT,

            answers_json TEXT,
            question_results_json TEXT,

            result_email_status TEXT NOT NULL DEFAULT 'not_sent',
            result_email_sent_at TEXT,
            result_email_error TEXT,

            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (assessment_id)
                REFERENCES assessments(id),

            FOREIGN KEY (student_id)
                REFERENCES students(id),

            UNIQUE (
                assessment_id,
                student_id,
                attempt_number
            )
        )
        """
    )

    print(
        "assessment_attempts table ready"
    )


# ============================================================
# RESULT INDEXES
# ============================================================


def create_indexes(
    connection: sqlite3.Connection,
) -> None:
    indexes = {
        "idx_attempts_assessment":
            """
            CREATE INDEX IF NOT EXISTS
            idx_attempts_assessment
            ON assessment_attempts(assessment_id)
            """,

        "idx_attempts_student":
            """
            CREATE INDEX IF NOT EXISTS
            idx_attempts_student
            ON assessment_attempts(student_id)
            """,

        "idx_attempts_submitted_at":
            """
            CREATE INDEX IF NOT EXISTS
            idx_attempts_submitted_at
            ON assessment_attempts(submitted_at)
            """,

        "idx_attempts_obtained_marks":
            """
            CREATE INDEX IF NOT EXISTS
            idx_attempts_obtained_marks
            ON assessment_attempts(obtained_marks)
            """,

        "idx_attempts_percentage":
            """
            CREATE INDEX IF NOT EXISTS
            idx_attempts_percentage
            ON assessment_attempts(percentage)
            """,

        "idx_attempts_status":
            """
            CREATE INDEX IF NOT EXISTS
            idx_attempts_status
            ON assessment_attempts(status)
            """,

        "idx_attempts_email_status":
            """
            CREATE INDEX IF NOT EXISTS
            idx_attempts_email_status
            ON assessment_attempts(result_email_status)
            """,

        "idx_attempts_assessment_student":
            """
            CREATE INDEX IF NOT EXISTS
            idx_attempts_assessment_student
            ON assessment_attempts(
                assessment_id,
                student_id
            )
            """,
    }

    for name, sql in indexes.items():
        connection.execute(sql)

        print(
            f"Index ready: {name}"
        )


# ============================================================
# RESULT VIEW
# ============================================================


def create_result_view(
    connection: sqlite3.Connection,
) -> None:
    """
    Create a stable query-friendly read model for
    Result / Analytics workflows.

    Important:
        answers_json and question_results_json are included here
        because ResultStore saves them and callers may need them
        after the result is persisted.
    """

    connection.execute(
        """
        DROP VIEW IF EXISTS student_result_view
        """
    )

    connection.execute(
        """
        CREATE VIEW student_result_view AS
        SELECT
            aa.id AS result_id,
            aa.assessment_id,
            aa.student_id,
            aa.attempt_number,

            s.student_no,
            s.university_roll,

            COALESCE(
                aa.student_name,
                s.name
            ) AS student_name,

            COALESCE(
                aa.student_email,
                s.email
            ) AS student_email,

            s.class_level AS student_class_level,
            s.section AS student_section,
            s.school_id AS student_school_id,

            a.title AS assessment_title,
            a.subject,
            a.chapter,
            a.topic,

            a.class_level AS assessment_class_level,
            a.section AS assessment_section,

            a.test_date,
            a.total_marks AS assessment_total_marks,

            a.form_id,
            a.responder_url,

            a.status AS assessment_status,

            aa.started_at,
            aa.submitted_at,

            aa.obtained_marks,
            aa.total_marks,
            aa.percentage,

            aa.correct_answers,
            aa.wrong_answers,
            aa.unanswered,

            aa.status AS result_status,

            aa.form_response_id,

            aa.answers_json,
            aa.question_results_json,

            aa.result_email_status,
            aa.result_email_sent_at,
            aa.result_email_error,

            aa.created_at AS result_created_at,
            aa.updated_at AS result_updated_at

        FROM assessment_attempts aa

        INNER JOIN students s
            ON s.id = aa.student_id

        INNER JOIN assessments a
            ON a.id = aa.assessment_id
        """
    )

    print(
        "View ready: student_result_view"
    )


# ============================================================
# VALIDATION
# ============================================================


def validate(
    connection: sqlite3.Connection,
) -> None:

    tables = {
        row[0]
        for row in connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        )
    }

    if "students" not in tables:
        raise RuntimeError(
            "Existing 'students' table not found."
        )

    if "assessments" not in tables:
        raise RuntimeError(
            "Existing 'assessments' table not found."
        )

    if "assessment_attempts" not in tables:
        raise RuntimeError(
            "assessment_attempts table was not created."
        )

    columns = table_columns(
        connection,
        "assessment_attempts",
    )

    required = {
        "assessment_id",
        "student_id",
        "attempt_number",

        "student_name",
        "student_email",

        "started_at",
        "submitted_at",

        "obtained_marks",
        "total_marks",
        "percentage",

        "correct_answers",
        "wrong_answers",
        "unanswered",

        "status",
        "form_response_id",

        "answers_json",
        "question_results_json",

        "result_email_status",
        "result_email_sent_at",
        "result_email_error",

        "created_at",
        "updated_at",
    }

    missing = sorted(
        required - columns
    )

    if missing:
        raise RuntimeError(
            "assessment_attempts is missing "
            "required columns: "
            + ", ".join(missing)
        )

    view_exists = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'view'
          AND name = 'student_result_view'
        """
    ).fetchone()

    if view_exists is None:
        raise RuntimeError(
            "student_result_view was not created."
        )

    count = connection.execute(
        """
        SELECT COUNT(*)
        FROM assessment_attempts
        """
    ).fetchone()[0]

    print(
        f"Current assessment_attempts rows: {count}"
    )


# ============================================================
# MAIN
# ============================================================


def main() -> int:
    global DB_PATH

    DB_PATH = resolve_db_path()

    print("=" * 60)
    print("TCO RESULT STORE MIGRATION")
    print("=" * 60)

    print(
        f"Database: {DB_PATH}"
    )

    if not DB_PATH.exists():
        print(
            "ERROR: Database file does not exist."
        )

        print(
            "Use the first command-line argument "
            "to pass the exact tco.db path."
        )

        return 1

    connection = sqlite3.connect(
        DB_PATH
    )

    try:
        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        # 1. Assessment test date
        add_test_date_column(
            connection
        )

        # 2. Result table
        create_result_table(
            connection
        )

        # 3. Result indexes
        create_indexes(
            connection
        )

        # 4. Result query view
        create_result_view(
            connection
        )

        # 5. Validate everything
        validate(
            connection
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    print("=" * 60)
    print("RESULT STORE MIGRATION COMPLETE")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )