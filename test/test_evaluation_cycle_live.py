from __future__ import annotations

import sys

from backend.services.evaluation_cycle import (
    EvaluationCycleError,
    EvaluationCycleService,
)


DEFAULT_FORM_ID = (
    "19dyN_cL_K1ElWXf0m9UWd-BAk7BtNzogXnj6OlMLD68"
)


def main() -> int:
    print("=" * 60)
    print("TCO GOOGLE FORMS → EVALUATION AGENT LIVE TEST")
    print("=" * 60)

    form_id = (
        sys.argv[1].strip()
        if len(sys.argv) > 1
        and sys.argv[1].strip()
        else DEFAULT_FORM_ID
    )

    print("Form ID:", form_id)
    print()

    service = EvaluationCycleService()

    try:
        results = service.evaluate_form(
            form_id=form_id,
            page_size=100,
        )
    except EvaluationCycleError as exc:
        print("EVALUATION CYCLE FAILED")
        print("Error:", exc)
        return 1
    except Exception as exc:
        print("UNEXPECTED FAILURE")
        print("Error:", exc)
        return 1

    print("Evaluated responses:", len(results))
    print()

    for index, result in enumerate(
        results,
        start=1,
    ):
        print(f"Response #{index}")
        print(
            "  Response ID:",
            result.get("response_id"),
        )
        print(
            "  Marks:",
            result.get("obtained_marks"),
            "/",
            result.get("total_marks"),
        )
        print(
            "  Percentage:",
            result.get("percentage"),
        )
        print(
            "  Correct:",
            result.get("correct_answers"),
        )
        print(
            "  Wrong:",
            result.get("wrong_answers"),
        )
        print(
            "  Unanswered:",
            result.get("unanswered"),
        )
        print(
            "  Review required:",
            result.get("review_required"),
        )

        print("  Question results:")

        for q in result.get(
            "question_results",
            [],
        ):
            print(
                "   -",
                q.get("question_id"),
                "|",
                q.get("status"),
                "|",
                q.get("marks_awarded"),
                "/",
                q.get("max_marks"),
            )

        print()

    print("=" * 60)
    print("TCO GOOGLE FORMS → EVALUATION AGENT LIVE TEST PASSED")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
