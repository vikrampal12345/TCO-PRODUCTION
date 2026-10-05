from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from backend.tools.google_forms_responses import (
    GoogleFormsResponsesTool,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "tco.db"


def resolve_form_id() -> str:
    """
    Use a form ID passed on the command line.
    Otherwise, try the latest assessment stored in SQLite.
    """

    if len(sys.argv) > 1 and sys.argv[1].strip():
        return sys.argv[1].strip()

    if not DB_PATH.exists():
        raise RuntimeError(
            f"Database not found: {DB_PATH}"
        )

    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute(
            """
            SELECT form_id
            FROM assessments
            WHERE form_id IS NOT NULL
              AND trim(form_id) != ''
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

    if not row:
        raise RuntimeError(
            "No assessment with a Google Form ID was found in tco.db. "
            "Pass the form ID explicitly."
        )

    return str(row[0]).strip()


def main() -> int:
    print("=" * 60)
    print("GOOGLE FORMS LIVE RESPONSE TEST")
    print("=" * 60)

    try:
        form_id = resolve_form_id()
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print("Form ID:", form_id)
    print(
        "This test will use the read-only Google Forms response scope:"
    )
    print(
        "https://www.googleapis.com/auth/forms.responses.readonly"
    )

    tool = GoogleFormsResponsesTool()

    result = tool.execute(
        operation="form.responses.list",
        form_id=form_id,
        page_size=100,
    )

    if not result.success:
        print("RESPONSE FETCH FAILED")
        print("Error code:", result.error_code)
        print("Error:", result.error_message)
        return 1

    data = result.data or {}
    responses = data.get("responses", [])

    print()
    print("Response count:", len(responses))
    print(
        "Next page token:",
        bool(data.get("next_page_token")),
    )

    for index, response in enumerate(responses, start=1):
        print()
        print(f"Response #{index}")
        print("  Response ID:", response.get("response_id"))
        print("  Submitted:", response.get("submitted_at"))
        print(
            "  Respondent email available:",
            bool(response.get("respondent_email")),
        )
        print(
            "  Answer count:",
            response.get("answer_count", 0),
        )

    print()
    print("=" * 60)
    print("GOOGLE FORMS LIVE RESPONSE TEST PASSED")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
