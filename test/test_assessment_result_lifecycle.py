from __future__ import annotations

from backend.services.assessment_result_lifecycle import (
    AssessmentResultLifecycleService,
)


# ============================================================
# FAKE EVALUATION CYCLE
# ============================================================

class FakeEvaluationCycle:
    """
    Fake EvaluationCycleService.

    This test focuses only on the orchestration between:

        EvaluationCycle
                ↓
        ResultEmailService
    """

    def __init__(
        self,
        *,
        status: str = "saved",
    ) -> None:
        self.status = status

        self.form_calls: list[dict] = []
        self.response_calls: list[dict] = []

    def evaluate_and_save_form(
        self,
        *,
        form_id: str,
        assessment_id: int,
        school_id: str | None = None,
        class_level: str | None = None,
        section: str | None = None,
        attempt_number: int = 1,
        page_size: int = 100,
    ) -> list[dict]:

        self.form_calls.append(
            {
                "form_id": form_id,
                "assessment_id": assessment_id,
                "school_id": school_id,
                "class_level": class_level,
                "section": section,
                "attempt_number": attempt_number,
                "page_size": page_size,
            }
        )

        if self.status == "review_required":
            return [
                {
                    "status": "review_required",
                    "response_id": (
                        "LIFECYCLE_RESPONSE_001"
                    ),
                    "evaluation": {
                        "review_required": True,
                    },
                    "saved_result": None,
                    "identity_method": None,
                }
            ]

        return [
            {
                "status": "saved",
                "response_id": (
                    "LIFECYCLE_RESPONSE_001"
                ),
                "identity_method": "student_no",
                "evaluation": {
                    "obtained_marks": 2.5,
                    "total_marks": 5.0,
                    "percentage": 50.0,
                },
                "saved_result": {
                    "result_id": 101,
                    "student_id": 2,
                    "student_name": "electro",
                    "student_email": (
                        "electrofact3@gmail.com"
                    ),
                    "obtained_marks": 2.5,
                    "total_marks": 5.0,
                    "percentage": 50.0,
                },
                "identity": {
                    "id": 2,
                    "student_no": "GMAIL_TEST_001",
                },
            }
        ]

    def evaluate_and_save_response(
        self,
        *,
        form_id: str,
        response_id: str,
        assessment_id: int,
        school_id: str | None = None,
        class_level: str | None = None,
        section: str | None = None,
        attempt_number: int = 1,
        page_size: int = 100,
    ) -> dict:

        self.response_calls.append(
            {
                "form_id": form_id,
                "response_id": response_id,
                "assessment_id": assessment_id,
                "school_id": school_id,
                "class_level": class_level,
                "section": section,
                "attempt_number": attempt_number,
                "page_size": page_size,
            }
        )

        return {
            "status": "saved",
            "response_id": response_id,
            "identity_method": "student_no",
            "evaluation": {
                "obtained_marks": 2.5,
                "total_marks": 5.0,
                "percentage": 50.0,
            },
            "saved_result": {
                "result_id": 101,
                "student_id": 2,
                "student_name": "electro",
                "student_email": (
                    "electrofact3@gmail.com"
                ),
                "obtained_marks": 2.5,
                "total_marks": 5.0,
                "percentage": 50.0,
            },
            "identity": {
                "id": 2,
                "student_no": "GMAIL_TEST_001",
            },
        }


# ============================================================
# FAKE RESULT EMAIL SERVICE
# ============================================================

class FakeResultEmailService:
    """
    Fake ResultEmailService.

    No real email is sent.
    """

    def __init__(
        self,
        *,
        status: str = "sent",
    ) -> None:
        self.status = status

        self.calls: list[dict] = []

    def send_result(
        self,
        *,
        result_id: int,
    ) -> dict:

        self.calls.append(
            {
                "result_id": result_id,
            }
        )

        if self.status == "sent":
            return {
                "status": "sent",
                "result_id": result_id,
                "recipient": (
                    "electrofact3@gmail.com"
                ),
                "subject": (
                    "TCO Assessment Result"
                ),
            }

        if self.status == "already_sent":
            return {
                "status": "already_sent",
                "result_id": result_id,
                "recipient": (
                    "electrofact3@gmail.com"
                ),
            }

        if self.status == "failed":
            return {
                "status": "failed",
                "result_id": result_id,
                "recipient": (
                    "electrofact3@gmail.com"
                ),
                "error": (
                    "Simulated Gmail failure."
                ),
            }

        return {
            "status": "skipped",
            "result_id": result_id,
        }


# ============================================================
# TEST 1
# FULL FORM -> RESULT -> EMAIL
# ============================================================

def test_full_form_lifecycle() -> None:

    evaluation_cycle = (
        FakeEvaluationCycle()
    )

    email_service = (
        FakeResultEmailService(
            status="sent"
        )
    )

    lifecycle_service = (
        AssessmentResultLifecycleService(
            evaluation_cycle=evaluation_cycle,
            result_email_service=email_service,
        )
    )

    results = (
        lifecycle_service.process_form(
            form_id="integration-test-form",
            assessment_id=10,
            school_id="TCO_TEST",
            class_level="TCO Test Class",
            section="TEST",
        )
    )

    assert len(results) == 1

    result = results[0]

    assert (
        result["status"]
        == "saved"
    )

    assert (
        result["saved_result"]
        ["result_id"]
        == 101
    )

    assert (
        result["lifecycle_status"]
        == "result_saved_email_sent"
    )

    assert (
        result["email"]
        ["status"]
        == "sent"
    )

    assert len(
        email_service.calls
    ) == 1

    assert (
        email_service.calls[0]
        ["result_id"]
        == 101
    )

    assert len(
        evaluation_cycle.form_calls
    ) == 1

    print(
        "SUCCESS: "
        "Full result -> email lifecycle works."
    )


# ============================================================
# TEST 2
# EMAIL FAILURE DOES NOT DELETE RESULT
# ============================================================

def test_email_failure_after_result_saved() -> None:

    evaluation_cycle = (
        FakeEvaluationCycle()
    )

    email_service = (
        FakeResultEmailService(
            status="failed"
        )
    )

    lifecycle_service = (
        AssessmentResultLifecycleService(
            evaluation_cycle=evaluation_cycle,
            result_email_service=email_service,
        )
    )

    result = (
        lifecycle_service.process_response(
            form_id="integration-test-form",
            response_id=(
                "LIFECYCLE_RESPONSE_001"
            ),
            assessment_id=10,
            school_id="TCO_TEST",
            class_level="TCO Test Class",
            section="TEST",
        )
    )

    assert (
        result["status"]
        == "saved"
    )

    assert (
        result["saved_result"]
        ["result_id"]
        == 101
    )

    assert (
        result["email"]
        ["status"]
        == "failed"
    )

    assert (
        result["lifecycle_status"]
        == "result_saved_email_failed"
    )

    print(
        "SUCCESS: "
        "Email failure does not affect saved result."
    )


# ============================================================
# TEST 3
# EMAIL DISABLED
# ============================================================

def test_email_disabled() -> None:

    evaluation_cycle = (
        FakeEvaluationCycle()
    )

    email_service = (
        FakeResultEmailService(
            status="sent"
        )
    )

    lifecycle_service = (
        AssessmentResultLifecycleService(
            evaluation_cycle=evaluation_cycle,
            result_email_service=email_service,
        )
    )

    result = (
        lifecycle_service.process_response(
            form_id="integration-test-form",
            response_id=(
                "LIFECYCLE_RESPONSE_001"
            ),
            assessment_id=10,
            send_email=False,
        )
    )

    assert (
        result["status"]
        == "saved"
    )

    assert (
        result["email"]
        ["status"]
        == "not_sent"
    )

    assert (
        result["email"]
        ["reason"]
        == "email_disabled"
    )

    assert (
        result["lifecycle_status"]
        == "result_saved_email_not_sent"
    )

    # Gmail/email service must not be called.

    assert len(
        email_service.calls
    ) == 0

    print(
        "SUCCESS: "
        "Email-disabled flow works."
    )


# ============================================================
# TEST 4
# REVIEW REQUIRED
# ============================================================

def test_review_required() -> None:

    evaluation_cycle = (
        FakeEvaluationCycle(
            status="review_required"
        )
    )

    email_service = (
        FakeResultEmailService(
            status="sent"
        )
    )

    lifecycle_service = (
        AssessmentResultLifecycleService(
            evaluation_cycle=evaluation_cycle,
            result_email_service=email_service,
        )
    )

    results = (
        lifecycle_service.process_form(
            form_id="integration-test-form",
            assessment_id=10,
        )
    )

    assert len(results) == 1

    result = results[0]

    assert (
        result["status"]
        == "review_required"
    )

    assert (
        result["email"]
        ["status"]
        == "not_sent"
    )

    assert (
        result["email"]
        ["reason"]
        == "review_required"
    )

    assert (
        result["lifecycle_status"]
        == "review_required"
    )

    # Email must NOT be sent when teacher review
    # is required.

    assert len(
        email_service.calls
    ) == 0

    print(
        "SUCCESS: "
        "Review-required flow blocks email."
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    print("=" * 60)

    print(
        "TCO ASSESSMENT RESULT LIFECYCLE TEST"
    )

    print("=" * 60)

    print()

    print(
        "TEST 1: FULL FORM -> RESULT -> EMAIL"
    )

    print(
        "-" * 60
    )

    test_full_form_lifecycle()

    print()

    print(
        "TEST 2: EMAIL FAILURE"
    )

    print(
        "-" * 60
    )

    test_email_failure_after_result_saved()

    print()

    print(
        "TEST 3: EMAIL DISABLED"
    )

    print(
        "-" * 60
    )

    test_email_disabled()

    print()

    print(
        "TEST 4: REVIEW REQUIRED"
    )

    print(
        "-" * 60
    )

    test_review_required()

    print()

    print("=" * 60)

    print(
        "ALL RESULT LIFECYCLE TESTS PASSED"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()