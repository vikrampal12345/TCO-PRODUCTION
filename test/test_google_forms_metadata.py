from __future__ import annotations

from backend.tools.google_forms_metadata import (
    GoogleFormsMetadataTool,
)


def main() -> None:
    print("=" * 60)
    print("GOOGLE FORMS METADATA NORMALIZATION TEST")
    print("=" * 60)

    sample_form = {
        "formId": "test-form-001",

        "info": {
            "title": "TCO - Computer Organization",
            "description": "Test quiz",
        },

        "settings": {
            "quizSettings": {
                "isQuiz": True,
            }
        },

        "responderUri": (
            "https://docs.google.com/forms/test"
        ),

        "revisionId": "revision-001",

        "items": [

            # =================================================
            # STUDENT ID / ROLL NUMBER FIELD
            # =================================================

            {
                "itemId": "identity-item",

                "title": "Student ID / Roll Number",

                "questionItem": {
                    "question": {
                        "questionId": "identity-question",

                        "required": True,

                        "textQuestion": {
                            "paragraph": False,
                        },
                    }
                },
            },

            # =================================================
            # ASSESSMENT QUESTION 1
            # =================================================

            {
                "itemId": "item-001",

                "title": "Which operation is ASL?",

                "questionItem": {
                    "question": {
                        "questionId": "question-001",

                        "required": True,

                        "grading": {
                            "pointValue": 4,

                            "correctAnswers": {
                                "answers": [
                                    {
                                        "value": (
                                            "Arithmetic shift left (ASL)"
                                        )
                                    }
                                ]
                            },
                        },

                        "choiceQuestion": {
                            "type": "RADIO",

                            "options": [
                                {
                                    "value": (
                                        "Logical shift right"
                                    )
                                },
                                {
                                    "value": (
                                        "Arithmetic shift left (ASL)"
                                    )
                                },
                                {
                                    "value": "Rotate left"
                                },
                                {
                                    "value": (
                                        "Arithmetic shift right"
                                    )
                                },
                            ],
                        },
                    }
                },
            },

            # =================================================
            # ASSESSMENT QUESTION 2
            # =================================================

            {
                "itemId": "item-002",

                "title": "What is the binary result?",

                "questionItem": {
                    "question": {
                        "questionId": "question-002",

                        "required": True,

                        "grading": {
                            "pointValue": 2,

                            "correctAnswers": {
                                "answers": [
                                    {
                                        "value": "00001100"
                                    }
                                ]
                            },
                        },

                        "textQuestion": {
                            "paragraph": False,
                        },
                    }
                },
            },
        ],
    }

    # =========================================================
    # NORMALIZE FORM
    # =========================================================

    normalized = GoogleFormsMetadataTool.normalize_form(
        form_id="test-form-001",
        form=sample_form,
    )

    # =========================================================
    # BASIC FORM ASSERTIONS
    # =========================================================

    assert normalized["form_id"] == (
        "test-form-001"
    )

    assert normalized["title"] == (
        "TCO - Computer Organization"
    )

    assert normalized["is_quiz"] is True

    # Identity field must NOT be counted as assessment question.
    assert normalized["question_count"] == 2

    # =========================================================
    # ASSESSMENT QUESTION 1
    # =========================================================

    first = normalized["questions"][0]

    assert first["item_id"] == "item-001"

    assert first["question_id"] == (
        "question-001"
    )

    assert first["question"] == (
        "Which operation is ASL?"
    )

    assert first["question_type"] == "radio"

    assert first["required"] is True

    assert first["options"] == [
        "Logical shift right",
        "Arithmetic shift left (ASL)",
        "Rotate left",
        "Arithmetic shift right",
    ]

    assert first["correct_answers"] == [
        "Arithmetic shift left (ASL)"
    ]

    assert first["accepted_answers"] == [
        "Arithmetic shift left (ASL)"
    ]

    assert first["correct_option"] == 2

    assert first["correct_option_indices"] == [
        2
    ]

    assert first["points"] == 4.0

    assert first["marks"] == 4.0

    assert first["has_grading"] is True

    # =========================================================
    # ASSESSMENT QUESTION 2
    # =========================================================

    second = normalized["questions"][1]

    assert second["item_id"] == "item-002"

    assert second["question_id"] == (
        "question-002"
    )

    assert second["question"] == (
        "What is the binary result?"
    )

    assert second["question_type"] == "text"

    assert second["required"] is True

    assert second["correct_answers"] == [
        "00001100"
    ]

    assert second["accepted_answers"] == [
        "00001100"
    ]

    assert second["points"] == 2.0

    assert second["marks"] == 2.0

    assert second["has_grading"] is True

    # =========================================================
    # ANSWER KEY ASSERTIONS
    # =========================================================

    assert len(
        normalized["answer_key"]
    ) == 2

    assert normalized["answer_key"][0][
        "question_id"
    ] == "question-001"

    assert normalized["answer_key"][0][
        "correct_option"
    ] == 2

    assert normalized["answer_key"][0][
        "marks"
    ] == 4.0

    assert normalized["answer_key"][1][
        "question_id"
    ] == "question-002"

    assert normalized["answer_key"][1][
        "correct_answers"
    ] == ["00001100"]

    assert normalized["answer_key"][1][
        "marks"
    ] == 2.0

    # =========================================================
    # MARKING SCHEME ASSERTIONS
    # =========================================================

    assert len(
        normalized["marking_scheme"]
    ) == 2

    assert normalized["marking_scheme"][0][
        "question_id"
    ] == "question-001"

    assert normalized["marking_scheme"][0][
        "max_marks"
    ] == 4.0

    assert normalized["marking_scheme"][1][
        "question_id"
    ] == "question-002"

    assert normalized["marking_scheme"][1][
        "max_marks"
    ] == 2.0

    # =========================================================
    # IDENTITY FIELD ASSERTIONS
    # =========================================================

    assert normalized["identity_field_count"] == 1

    assert len(
        normalized["identity_fields"]
    ) == 1

    identity = normalized["identity_fields"][0]

    assert identity["item_id"] == (
        "identity-item"
    )

    assert identity["question_id"] == (
        "identity-question"
    )

    assert identity["title"] == (
        "Student ID / Roll Number"
    )

    assert identity["required"] is True

    assert identity["question_type"] == "text"

    assert identity["identity_type"] == (
        "student_id_or_roll_number"
    )

    # =========================================================
    # CRITICAL SAFETY CHECKS
    # =========================================================

    # Identity field must NOT appear inside questions.
    question_ids = [
        question["question_id"]
        for question in normalized["questions"]
    ]

    assert "identity-question" not in (
        question_ids
    )

    # Identity field must NOT appear inside answer key.
    answer_key_ids = [
        item["question_id"]
        for item in normalized["answer_key"]
    ]

    assert "identity-question" not in (
        answer_key_ids
    )

    # Identity field must NOT appear inside marking scheme.
    marking_ids = [
        item["question_id"]
        for item in normalized["marking_scheme"]
    ]

    assert "identity-question" not in (
        marking_ids
    )

    # =========================================================
    # PRINT RESULTS
    # =========================================================

    print("Form:", normalized["title"])

    print("Quiz:", normalized["is_quiz"])

    print(
        "Assessment questions:",
        normalized["question_count"],
    )

    print(
        "Identity fields:",
        normalized["identity_field_count"],
    )

    print()

    # ---------------------------------------------------------
    # Identity field output
    # ---------------------------------------------------------

    print("IDENTITY FIELD")
    print("-" * 60)

    for identity in normalized[
        "identity_fields"
    ]:
        print(
            "  Item ID:",
            identity["item_id"],
        )

        print(
            "  Question ID:",
            identity["question_id"],
        )

        print(
            "  Title:",
            identity["title"],
        )

        print(
            "  Type:",
            identity["question_type"],
        )

        print(
            "  Required:",
            identity["required"],
        )

        print(
            "  Identity Type:",
            identity["identity_type"],
        )

    print()

    # ---------------------------------------------------------
    # Assessment questions output
    # ---------------------------------------------------------

    print("ASSESSMENT QUESTIONS")
    print("-" * 60)

    for index, question in enumerate(
        normalized["questions"],
        start=1,
    ):
        print(f"Question #{index}")

        print(
            "  Item ID:",
            question["item_id"],
        )

        print(
            "  Question ID:",
            question["question_id"],
        )

        print(
            "  Type:",
            question["question_type"],
        )

        print(
            "  Question:",
            question["question"],
        )

        print(
            "  Marks:",
            question["marks"],
        )

        print(
            "  Correct:",
            question["correct_answers"],
        )

        print(
            "  Correct option:",
            question["correct_option"],
        )

        print()

    # =========================================================
    # FINAL SUCCESS
    # =========================================================

    print("=" * 60)
    print(
        "GOOGLE FORMS METADATA NORMALIZATION TEST PASSED"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()