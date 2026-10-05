from __future__ import annotations

from pathlib import Path

from backend.services.student_identity import (
    StudentIdentityError,
    StudentIdentityResolver,
)


DB_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "tco.db"
)


def print_student(label: str, result: dict) -> None:
    print(f"\n{label}")
    print("-" * 60)
    print("Status:", result["status"])
    print("Method:", result["method"])
    print("Message:", result["message"])
    print("Match count:", result["match_count"])

    if result["student"]:
        student = result["student"]

        print("Student ID:", student["student_id"])
        print("Student No:", student["student_no"])
        print("University Roll:", student["university_roll"])
        print("Name:", student["name"])
        print("Email:", student["email"])
        print("Class:", student["class_level"])
        print("Section:", student["section"])
        print("School:", student["school_id"])


def main() -> None:
    print("=" * 60)
    print("TCO STUDENT IDENTITY TEST")
    print("=" * 60)
    print("Database:", DB_PATH)

    resolver = StudentIdentityResolver(
        db_path=DB_PATH
    )

    # --------------------------------------------------------
    # Find the known test student by email.
    # This does NOT modify the database.
    # --------------------------------------------------------

    email_result = resolver.resolve(
        email="electrofact3@gmail.com",
        school_id="TCO_TEST",
        class_level="TCO Test Class",
        section="TEST",
    )

    print_student(
        "1. EMAIL MATCH",
        email_result,
    )

    assert email_result["status"] == "matched"
    assert email_result["method"] == "email"
    assert email_result["student"] is not None

    student = email_result["student"]

    # --------------------------------------------------------
    # Match the same student by name.
    # Context filters make this deterministic.
    # --------------------------------------------------------

    name_result = resolver.resolve(
        name=student["name"],
        school_id="TCO_TEST",
        class_level="TCO Test Class",
        section="TEST",
    )

    print_student(
        "2. NAME MATCH",
        name_result,
    )

    assert name_result["status"] == "matched"
    assert name_result["method"] == "name"
    assert (
        name_result["student"]["student_id"]
        == student["student_id"]
    )

    # --------------------------------------------------------
    # Match using internal database student_id.
    # --------------------------------------------------------

    id_result = resolver.resolve(
        student_id=student["student_id"],
        school_id="TCO_TEST",
    )

    print_student(
        "3. DATABASE STUDENT_ID MATCH",
        id_result,
    )

    assert id_result["status"] == "matched"
    assert (
        id_result["method"]
        == "database_student_id"
    )
    assert (
        id_result["student"]["student_id"]
        == student["student_id"]
    )

    # --------------------------------------------------------
    # Priority test:
    # email must win over name.
    # --------------------------------------------------------

    priority_result = resolver.resolve(
        email=student["email"],
        name="This Name Should Not Match",
        school_id="TCO_TEST",
    )

    print_student(
        "4. PRIORITY TEST",
        priority_result,
    )

    assert priority_result["status"] == "matched"
    assert priority_result["method"] == "email"
    assert (
        priority_result["student"]["student_id"]
        == student["student_id"]
    )

    # --------------------------------------------------------
    # Not found test.
    # --------------------------------------------------------

    not_found_result = resolver.resolve(
        student_no="DOES_NOT_EXIST_999999",
        school_id="TCO_TEST",
    )

    print_student(
        "5. NOT FOUND TEST",
        not_found_result,
    )

    assert not_found_result["status"] == "not_found"
    assert not_found_result["student"] is None

    # --------------------------------------------------------
    # Missing identity test.
    # --------------------------------------------------------

    try:
        resolver.resolve(
            school_id="TCO_TEST"
        )

    except StudentIdentityError as exc:
        print("\n6. VALIDATION TEST")
        print("-" * 60)
        print("Validation passed:", exc)

    else:
        raise AssertionError(
            "Expected StudentIdentityError was not raised."
        )

    print("\n" + "=" * 60)
    print("STUDENT IDENTITY TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()