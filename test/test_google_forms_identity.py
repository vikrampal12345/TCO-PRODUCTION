from __future__ import annotations

from backend.tools.google_forms_identity import (
    GoogleFormsIdentityTool,
)


def main() -> None:
    print("=" * 60)
    print(
        "TCO GOOGLE FORMS IDENTITY TOOL TEST"
    )
    print("=" * 60)

    # --------------------------------------------------------
    # Build request.
    # --------------------------------------------------------

    request = (
        GoogleFormsIdentityTool
        .build_create_request(
            index=0,
            required=True,
        )
    )

    create_item = request[
        "createItem"
    ]

    item = create_item[
        "item"
    ]

    question = (
        item[
            "questionItem"
        ][
            "question"
        ]
    )

    print("\nCREATE REQUEST")
    print("-" * 60)

    print(
        "Title:",
        item["title"],
    )

    print(
        "Required:",
        question["required"],
    )

    print(
        "Paragraph:",
        question[
            "textQuestion"
        ]["paragraph"],
    )

    print(
        "Location:",
        create_item[
            "location"
        ]["index"],
    )

    assert (
        item["title"]
        == "Student ID / Roll Number"
    )

    assert (
        question["required"]
        is True
    )

    assert (
        question[
            "textQuestion"
        ]["paragraph"]
        is False
    )

    assert (
        create_item[
            "location"
        ]["index"]
        == 0
    )

    # --------------------------------------------------------
    # Existing form detection.
    # --------------------------------------------------------

    sample_form = {
        "formId": "test-form-001",
        "items": [
            {
                "itemId": "item-identity",
                "title": (
                    "Student ID / Roll Number"
                ),
                "questionItem": {
                    "question": {
                        "questionId": (
                            "question-identity"
                        ),
                        "required": True,
                        "textQuestion": {
                            "paragraph": False,
                        },
                    }
                },
            },
            {
                "itemId": "item-q1",
                "title": "Question 1",
                "questionItem": {
                    "question": {
                        "questionId": "q1",
                        "required": True,
                    }
                },
            },
        ],
    }

    fields = (
        GoogleFormsIdentityTool
        .find_identity_fields(
            sample_form
        )
    )

    print("\nIDENTITY FIELD DETECTION")
    print("-" * 60)

    print(
        "Found:",
        len(fields),
    )

    assert len(fields) == 1

    assert (
        fields[0]["item_id"]
        == "item-identity"
    )

    assert (
        fields[0]["question_id"]
        == "question-identity"
    )

    assert (
        fields[0]["required"]
        is True
    )

    # --------------------------------------------------------
    # No identity field.
    # --------------------------------------------------------

    empty_form = {
        "formId": "empty-form",
        "items": [
            {
                "itemId": "item-q1",
                "title": "Question 1",
                "questionItem": {
                    "question": {
                        "questionId": "q1",
                    }
                },
            }
        ],
    }

    empty_fields = (
        GoogleFormsIdentityTool
        .find_identity_fields(
            empty_form
        )
    )

    print(
        "Without identity field:",
        len(empty_fields),
    )

    assert (
        empty_fields == []
    )

    print("\n" + "=" * 60)
    print(
        "GOOGLE FORMS IDENTITY TOOL TEST PASSED"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()