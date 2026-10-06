from __future__ import annotations

from typing import Any


class FakeMetadataTool:
    def execute(
        self,
        operation: str,
        *,
        form_id: str,
    ):
        from backend.core.tool_result import ToolResult

        questions = [
            {
                "question_id": "q1",
                "question": "Which operation is ASL?",
                "question_type": "radio",
                "options": [
                    "Logical shift right",
                    "Arithmetic shift left (ASL)",
                    "Rotate left",
                    "Arithmetic shift right",
                ],
                "marks": 4.0,
            },
            {
                "question_id": "q2",
                "question": "What action occurs for bit pair 10?",
                "question_type": "radio",
                "options": [
                    "Add M then ASR",
                    "Subtract M then ASR",
                    "ASR only",
                    "No operation",
                ],
                "marks": 4.0,
            },
        ]

        answer_key = [
            {
                "question_id": "q1",
                "correct_answers": [
                    "Arithmetic shift left (ASL)"
                ],
                "accepted_answers": [
                    "Arithmetic shift left (ASL)"
                ],
                "correct_option": 2,
                "marks": 4.0,
                "points": 4.0,
            },
            {
                "question_id": "q2",
                "correct_answers": [
                    "Add M then ASR"
                ],
                "accepted_answers": [
                    "Add M then ASR"
                ],
                "correct_option": 1,
                "marks": 4.0,
                "points": 4.0,
            },
        ]

        return ToolResult.ok(
            data={
                "form_id": form_id,
                "title": "Integration Test Form",
                "questions": questions,
                "answer_key": answer_key,
                "marking_scheme": [
                    {
                        "question_id": "q1",
                        "max_marks": 4.0,
                    },
                    {
                        "question_id": "q2",
                        "max_marks": 4.0,
                    },
                ],
            }
        )


class FakeResponseTool:
    def execute(
        self,
        operation: str,
        *,
        form_id: str,
        page_size: int = 100,
    ):
        from backend.core.tool_result import ToolResult

        return ToolResult.ok(
            data={
                "responses": [
                    {
                        "response_id": "response-001",
                        "submitted_at": "2026-10-05T10:00:00Z",
                        "respondent_email": "test@example.com",
                        "answers": [
                            {
                                "question_id": "q1",
                                "values": [
                                    "Arithmetic shift left (ASL)"
                                ],
                            },
                            {
                                "question_id": "q2",
                                "values": [
                                    "Wrong answer"
                                ],
                            },
                        ],
                    }
                ]
            }
        )


def build_service():
    from backend.agents.evaluation_agent import EvaluationAgent
    from backend.services.evaluation_cycle import EvaluationCycleService

    return EvaluationCycleService(
        metadata_tool=FakeMetadataTool(),
        response_tool=FakeResponseTool(),
        evaluation_agent=EvaluationAgent(
            model=object()
        ),
    )


def main() -> int:
    print("=" * 60)
    print("TCO EVALUATION CYCLE TEST")
    print("=" * 60)

    service = build_service()

    results = service.evaluate_form(
        form_id="test-form-001"
    )

    assert len(results) == 1

    result = results[0]

    assert result["submission_source"] == "google_forms"
    assert result["response_id"] == "response-001"
    assert result["obtained_marks"] == 4.0
    assert result["total_marks"] == 8.0
    assert result["percentage"] == 50.0
    assert result["correct_answers"] == 1
    assert result["wrong_answers"] == 1
    assert result["unanswered"] == 0

    print("Form ID:", result["form_id"])
    print("Response ID:", result["response_id"])
    print(
        "Marks:",
        result["obtained_marks"],
        "/",
        result["total_marks"],
    )
    print("Percentage:", result["percentage"])
    print("Correct:", result["correct_answers"])
    print("Wrong:", result["wrong_answers"])
    print("Unanswered:", result["unanswered"])

    print("=" * 60)
    print("TCO EVALUATION CYCLE TEST PASSED")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
