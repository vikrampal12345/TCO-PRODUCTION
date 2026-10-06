from backend.agents.evaluation_agent import EvaluationAgent


def main() -> None:
    agent = EvaluationAgent(
        model=object(),
    )

    questions = [
        {
            "question_id": "q1",
            "question": "2 + 2 = ?",
            "question_type": "mcq",
            "options": [
                "3",
                "4",
                "5",
                "6",
            ],
            "marks": 1,
        },
        {
            "question_id": "q2",
            "question": "Which language is used for TCO backend?",
            "question_type": "mcq",
            "options": [
                "Java",
                "Python",
                "C++",
                "Go",
            ],
            "marks": 1,
        },
    ]

    answer_key = [
        {
            "question_id": "q1",
            "correct_option": 2,
        },
        {
            "question_id": "q2",
            "correct_option": 2,
        },
    ]

    # Google Forms-shaped answers.
    google_form_answers = [
        {
            "question_id": "q1",
            "values": ["4"],
        },
        {
            "question_id": "q2",
            "values": ["Python"],
        },
    ]

    normalized_forms = agent.normalize_submission_answers(
        google_form_answers
    )

    assert normalized_forms[0]["answer"] == ["4"]
    assert normalized_forms[1]["answer"] == ["Python"]

    forms_result = agent.evaluate_submission(
        questions=questions,
        answer_key=answer_key,
        marking_scheme=[],
        submission={
            "submission_id": "form-response-001",
            "student_name": "Test Student",
            "answers": google_form_answers,
        },
        submission_source="google_forms",
    )

    assert forms_result["obtained_marks"] == 2.0
    assert forms_result["total_marks"] == 2.0
    assert forms_result["percentage"] == 100.0
    assert forms_result["correct_answers"] == 2
    assert forms_result["wrong_answers"] == 0
    assert forms_result["unanswered"] == 0

    # Future scanned-copy-shaped answers.
    #
    # OCR/Vision will eventually produce text plus confidence
    # and page/region metadata. Evaluation Agent should not
    # need any change for that source.
    scanned_answers = [
        {
            "question_id": "q1",
            "text": "4",
            "confidence": 0.98,
            "source_locator": {
                "page": 1,
                "region": "answer_q1",
            },
        },
        {
            "question_id": "q2",
            "text": "Python",
            "confidence": 0.95,
            "source_locator": {
                "page": 1,
                "region": "answer_q2",
            },
        },
    ]

    normalized_scan = agent.normalize_submission_answers(
        scanned_answers
    )

    assert normalized_scan[0]["answer"] == "4"
    assert normalized_scan[0]["confidence"] == 0.98
    assert normalized_scan[0]["source_locator"]["page"] == 1

    scan_result = agent.evaluate_submission(
        questions=questions,
        answer_key=answer_key,
        marking_scheme=[],
        submission={
            "submission_id": "scan-001",
            "student_name": "Scanned Student",
            "answers": scanned_answers,
        },
        submission_source="scanned_copy",
    )

    assert scan_result["obtained_marks"] == 2.0
    assert scan_result["total_marks"] == 2.0
    assert scan_result["percentage"] == 100.0
    assert scan_result["correct_answers"] == 2

    print("=" * 60)
    print("TCO EVALUATION AGENT TEST")
    print("=" * 60)
    print("Google Forms:")
    print("  Source:", forms_result["submission_source"])
    print("  Marks:", forms_result["obtained_marks"], "/", forms_result["total_marks"])
    print("  Percentage:", forms_result["percentage"])
    print()
    print("Scanned Copy:")
    print("  Source:", scan_result["submission_source"])
    print("  Marks:", scan_result["obtained_marks"], "/", scan_result["total_marks"])
    print("  Percentage:", scan_result["percentage"])
    print("=" * 60)
    print("EVALUATION AGENT FUTURE-SOURCE TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
