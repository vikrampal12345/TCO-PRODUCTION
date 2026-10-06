from __future__ import annotations

import sys

from backend.tools.google_forms_metadata import (
    GoogleFormsMetadataTool,
)


def main() -> int:
    print("=" * 60)
    print("GOOGLE FORMS LIVE METADATA TEST")
    print("=" * 60)

    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print(
            "ERROR: Pass a Google Form ID."
        )
        print(
            "Example:"
        )
        print(
            "python -m test.test_google_forms_metadata_live "
            "FORM_ID"
        )
        return 1

    form_id = sys.argv[1].strip()

    print("Form ID:", form_id)
    print(
        "OAuth scope:",
        "https://www.googleapis.com/auth/forms.body.readonly",
    )
    print()

    tool = GoogleFormsMetadataTool()

    result = tool.execute(
        operation="form.metadata.get",
        form_id=form_id,
    )

    if not result.success:
        print("FORM METADATA FETCH FAILED")
        print("Error code:", result.error_code)
        print("Error:", result.error_message)
        return 1

    data = result.data or {}

    print("Title:", data.get("title"))
    print("Quiz:", data.get("is_quiz"))
    print("Responder URL:", data.get("responder_url"))
    print("Question count:", data.get("question_count"))
    print()

    for index, question in enumerate(
        data.get("questions", []),
        start=1,
    ):
        print(f"Question #{index}")
        print(
            "  Question ID:",
            question.get("question_id"),
        )
        print(
            "  Type:",
            question.get("question_type"),
        )
        print(
            "  Question:",
            question.get("question"),
        )
        print(
            "  Marks:",
            question.get("marks"),
        )
        print(
            "  Options:",
            question.get("options"),
        )
        print(
            "  Correct answers:",
            question.get("correct_answers"),
        )
        print(
            "  Correct option:",
            question.get("correct_option"),
        )
        print()

    print("=" * 60)
    print("GOOGLE FORMS LIVE METADATA TEST PASSED")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
