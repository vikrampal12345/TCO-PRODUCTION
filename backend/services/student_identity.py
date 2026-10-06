from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "tco.db"
)


class StudentIdentityError(RuntimeError):
    """Raised when student identity resolution fails."""


class StudentIdentityResolver:
    """
    Deterministic student identity resolver.

    Purpose:
        Convert identity information from a submission into one
        database student record.

    Priority:
        1. database student_id
        2. student_no
        3. university_roll
        4. email
        5. name

    Important:
        - Does not use an LLM.
        - Does not evaluate answers.
        - Does not save results.
        - Does not send emails.
        - Only resolves a submitted identity to a student record.
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
    ) -> None:
        self.db_path = Path(
            db_path or DEFAULT_DB_PATH
        ).resolve()

        if not self.db_path.exists():
            raise StudentIdentityError(
                f"Database file does not exist: {self.db_path}"
            )

    # =========================================================
    # DATABASE
    # =========================================================

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.db_path
        )
        connection.row_factory = sqlite3.Row
        connection.execute(
            "PRAGMA foreign_keys = ON"
        )
        return connection

    # =========================================================
    # NORMALIZATION
    # =========================================================

    @staticmethod
    def _clean(value: Any) -> str:
        if value is None:
            return ""

        return str(value).strip()

    @classmethod
    def _clean_email(cls, value: Any) -> str:
        return cls._clean(value).lower()

    # =========================================================
    # STUDENT ROW
    # =========================================================

    @staticmethod
    def _student_row_to_dict(
        row: sqlite3.Row,
    ) -> dict[str, Any]:
        return {
            "student_id": row["id"],
            "student_no": row["student_no"],
            "university_roll": row["university_roll"],
            "name": row["name"],
            "email": row["email"],
            "class_level": row["class_level"],
            "section": row["section"],
            "school_id": row["school_id"],
            "phone": row["phone"],
            "course": row["course"],
            "semester": row["semester"],
            "is_active": row["is_active"],
        }

    # =========================================================
    # BUILD CONDITIONS
    # =========================================================

    def _context_conditions(
        self,
        *,
        school_id: str | None,
        class_level: str | None,
        section: str | None,
    ) -> tuple[list[str], list[Any]]:
        conditions: list[str] = [
            "COALESCE(is_active, 1) = 1"
        ]

        parameters: list[Any] = []

        if school_id:
            conditions.append(
                "school_id = ?"
            )
            parameters.append(
                school_id
            )

        if class_level:
            conditions.append(
                "LOWER(TRIM(class_level)) = LOWER(TRIM(?))"
            )
            parameters.append(
                class_level
            )

        if section:
            conditions.append(
                "LOWER(TRIM(section)) = LOWER(TRIM(?))"
            )
            parameters.append(
                section
            )

        return conditions, parameters

    # =========================================================
    # QUERY SINGLE FIELD
    # =========================================================

    def _find_by_field(
        self,
        *,
        field: str,
        value: str,
        school_id: str | None,
        class_level: str | None,
        section: str | None,
    ) -> list[dict[str, Any]]:
        allowed_fields = {
            "student_no",
            "university_roll",
            "email",
            "name",
        }

        if field not in allowed_fields:
            raise StudentIdentityError(
                f"Unsupported student lookup field: {field}"
            )

        conditions, parameters = (
            self._context_conditions(
                school_id=school_id,
                class_level=class_level,
                section=section,
            )
        )

        if field == "email":
            conditions.append(
                "LOWER(TRIM(email)) = LOWER(TRIM(?))"
            )
        else:
            conditions.append(
                f"LOWER(TRIM({field})) = LOWER(TRIM(?))"
            )

        parameters.append(value)

        query = f"""
            SELECT
                id,
                student_no,
                university_roll,
                name,
                email,
                class_level,
                section,
                school_id,
                phone,
                course,
                semester,
                is_active
            FROM students
            WHERE {" AND ".join(conditions)}
            ORDER BY id
        """

        with self._connect() as connection:
            rows = connection.execute(
                query,
                parameters,
            ).fetchall()

        return [
            self._student_row_to_dict(row)
            for row in rows
        ]

    # =========================================================
    # FIND BY INTERNAL DATABASE ID
    # =========================================================

    def _find_by_database_id(
        self,
        *,
        student_id: int,
        school_id: str | None,
        class_level: str | None,
        section: str | None,
    ) -> list[dict[str, Any]]:
        conditions, parameters = (
            self._context_conditions(
                school_id=school_id,
                class_level=class_level,
                section=section,
            )
        )

        conditions.append("id = ?")
        parameters.append(student_id)

        query = f"""
            SELECT
                id,
                student_no,
                university_roll,
                name,
                email,
                class_level,
                section,
                school_id,
                phone,
                course,
                semester,
                is_active
            FROM students
            WHERE {" AND ".join(conditions)}
        """

        with self._connect() as connection:
            rows = connection.execute(
                query,
                parameters,
            ).fetchall()

        return [
            self._student_row_to_dict(row)
            for row in rows
        ]

    # =========================================================
    # RESOLVE
    # =========================================================

    def resolve(
        self,
        *,
        student_id: int | None = None,
        student_no: str | None = None,
        university_roll: str | None = None,
        email: str | None = None,
        name: str | None = None,
        school_id: str | None = None,
        class_level: str | None = None,
        section: str | None = None,
    ) -> dict[str, Any]:
        """
        Resolve one student from available identity information.

        Returns:
            {
                "status": "matched" | "ambiguous" | "not_found",
                "method": "...",
                "student": {...} | None,
                "candidates": [...],
                "match_count": int,
                "message": str
            }
        """

        school_id = self._clean(
            school_id
        ) or None

        class_level = self._clean(
            class_level
        ) or None

        section = self._clean(
            section
        ) or None

        student_no = self._clean(
            student_no
        ) or None

        university_roll = self._clean(
            university_roll
        ) or None

        email = self._clean_email(
            email
        ) or None

        name = self._clean(
            name
        ) or None

        # -----------------------------------------------------
        # 1. DATABASE STUDENT ID
        # -----------------------------------------------------

        if student_id is not None:
            try:
                student_id = int(student_id)
            except (TypeError, ValueError):
                raise StudentIdentityError(
                    "student_id must be an integer."
                )

            if student_id <= 0:
                raise StudentIdentityError(
                    "student_id must be greater than 0."
                )

            candidates = self._find_by_database_id(
                student_id=student_id,
                school_id=school_id,
                class_level=class_level,
                section=section,
            )

            if len(candidates) == 1:
                return {
                    "status": "matched",
                    "method": "database_student_id",
                    "student": candidates[0],
                    "candidates": candidates,
                    "match_count": 1,
                    "message": (
                        "Student matched using database student_id."
                    ),
                }

            if len(candidates) > 1:
                return {
                    "status": "ambiguous",
                    "method": "database_student_id",
                    "student": None,
                    "candidates": candidates,
                    "match_count": len(candidates),
                    "message": (
                        "Multiple students matched the database student_id."
                    ),
                }

        # -----------------------------------------------------
        # 2. STUDENT NUMBER
        # -----------------------------------------------------

        if student_no:
            candidates = self._find_by_field(
                field="student_no",
                value=student_no,
                school_id=school_id,
                class_level=class_level,
                section=section,
            )

            if len(candidates) == 1:
                return {
                    "status": "matched",
                    "method": "student_no",
                    "student": candidates[0],
                    "candidates": candidates,
                    "match_count": 1,
                    "message": (
                        "Student matched using student_no."
                    ),
                }

            if len(candidates) > 1:
                return {
                    "status": "ambiguous",
                    "method": "student_no",
                    "student": None,
                    "candidates": candidates,
                    "match_count": len(candidates),
                    "message": (
                        "Multiple students matched the student_no."
                    ),
                }

        # -----------------------------------------------------
        # 3. UNIVERSITY ROLL
        # -----------------------------------------------------

        if university_roll:
            candidates = self._find_by_field(
                field="university_roll",
                value=university_roll,
                school_id=school_id,
                class_level=class_level,
                section=section,
            )

            if len(candidates) == 1:
                return {
                    "status": "matched",
                    "method": "university_roll",
                    "student": candidates[0],
                    "candidates": candidates,
                    "match_count": 1,
                    "message": (
                        "Student matched using university_roll."
                    ),
                }

            if len(candidates) > 1:
                return {
                    "status": "ambiguous",
                    "method": "university_roll",
                    "student": None,
                    "candidates": candidates,
                    "match_count": len(candidates),
                    "message": (
                        "Multiple students matched the university_roll."
                    ),
                }

        # -----------------------------------------------------
        # 4. EMAIL
        # -----------------------------------------------------

        if email:
            candidates = self._find_by_field(
                field="email",
                value=email,
                school_id=school_id,
                class_level=class_level,
                section=section,
            )

            if len(candidates) == 1:
                return {
                    "status": "matched",
                    "method": "email",
                    "student": candidates[0],
                    "candidates": candidates,
                    "match_count": 1,
                    "message": (
                        "Student matched using email."
                    ),
                }

            if len(candidates) > 1:
                return {
                    "status": "ambiguous",
                    "method": "email",
                    "student": None,
                    "candidates": candidates,
                    "match_count": len(candidates),
                    "message": (
                        "Multiple students matched the email."
                    ),
                }

        # -----------------------------------------------------
        # 5. NAME
        # -----------------------------------------------------

        if name:
            candidates = self._find_by_field(
                field="name",
                value=name,
                school_id=school_id,
                class_level=class_level,
                section=section,
            )

            if len(candidates) == 1:
                return {
                    "status": "matched",
                    "method": "name",
                    "student": candidates[0],
                    "candidates": candidates,
                    "match_count": 1,
                    "message": (
                        "Student matched using name."
                    ),
                }

            if len(candidates) > 1:
                return {
                    "status": "ambiguous",
                    "method": "name",
                    "student": None,
                    "candidates": candidates,
                    "match_count": len(candidates),
                    "message": (
                        "Multiple students matched the name. "
                        "A stronger identifier is required."
                    ),
                }

        # -----------------------------------------------------
        # NOTHING MATCHED
        # -----------------------------------------------------

        provided_identifiers = [
            value
            for value in (
                student_id,
                student_no,
                university_roll,
                email,
                name,
            )
            if value is not None
        ]

        if not provided_identifiers:
            raise StudentIdentityError(
                "Provide at least one student identity field."
            )

        return {
            "status": "not_found",
            "method": None,
            "student": None,
            "candidates": [],
            "match_count": 0,
            "message": (
                "No active student matched the provided identity."
            ),
        }


def resolve_student_identity(
    *,
    student_id: int | None = None,
    student_no: str | None = None,
    university_roll: str | None = None,
    email: str | None = None,
    name: str | None = None,
    school_id: str | None = None,
    class_level: str | None = None,
    section: str | None = None,
) -> dict[str, Any]:
    """
    Backward/simple functional API.
    """

    resolver = StudentIdentityResolver()

    return resolver.resolve(
        student_id=student_id,
        student_no=student_no,
        university_roll=university_roll,
        email=email,
        name=name,
        school_id=school_id,
        class_level=class_level,
        section=section,
    )