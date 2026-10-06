from __future__ import annotations

from backend.tools.google_forms_responses import (
    GoogleFormsResponsesTool,
)


def main() -> None:
    print("=" * 60)
    print("GOOGLE FORMS RESPONSE NORMALIZATION TEST")
    print("=" * 60)

    sample_response = {
        "formId": "test-form-123",
        "responseId": "response-001",
        "createTime": "2026-10-05T10:00:00Z",
        "lastSubmittedTime": "2026-10-05T10:07:12Z",
        "respondentEmail": "student@example.com",
        "answers": {
            "question-1": {
                "questionId": "question-1",
                "textAnswers": {
                    "answers": [
                        {"value": "Option A"}
                    ]
                }
            },
            "question-2": {
                "questionId": "question-2",
                "textAnswers": {
                    "answers": [
                        {"value": "Booth Algorithm"}
                    ]
                }
            },
        },
    }

    normalized = GoogleFormsResponsesTool.normalize_response(
        form_id="test-form-123",
        response=sample_response,
    )

    assert normalized["form_id"] == "test-form-123"
    assert normalized["response_id"] == "response-001"
    assert (
        normalized["submitted_at"]
        == "2026-10-05T10:07:12Z"
    )
    assert (
        normalized["respondent_email"]
        == "student@example.com"
    )
    assert normalized["answer_count"] == 2
    assert (
        normalized["answers"][0]["question_id"]
        == "question-1"
    )
    assert normalized["answers"][0]["values"] == ["Option A"]

    print("Form ID:", normalized["form_id"])
    print("Response ID:", normalized["response_id"])
    print("Submitted:", normalized["submitted_at"])
    print("Respondent:", normalized["respondent_email"])
    print("Answers:", normalized["answer_count"])

    print("=" * 60)
    print("GOOGLE FORMS RESPONSE NORMALIZATION TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
