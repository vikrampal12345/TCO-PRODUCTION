from __future__ import annotations


from backend.copy_checker.schemas.submission import AggregatedAnswer
from pathlib import Path
from typing import Callable

from PIL import Image

from backend.copy_checker.core.config import settings
from backend.copy_checker.schemas.evaluation_result import EvaluationResult
from backend.copy_checker.schemas.marking_scheme import MarkingScheme
from backend.copy_checker.schemas.submission import AggregatedSubmission
from backend.copy_checker.services.checked_copy_renderer import CheckedCopyRenderer
from backend.copy_checker.services.grading_model import GradingModel
from backend.copy_checker.services.submission_aggregation_service import SubmissionAggregationService


class SubmissionReviewRequired(ValueError):
    """Raised when extracted answers require teacher review before grading."""

    def __init__(self, submission: AggregatedSubmission) -> None:
        self.submission = submission
        message = (
            "Combined extraction requires review before grading. "
            f"Warnings: {submission.warnings}"
        )
        super().__init__(message)


class InMemoryGradingWorkflow:
    """
    Pipeline:

        PDF
        ↓
        Whole-page extraction
        ↓
        Combine / aggregate
        ↓
        Locked marking scheme
        ↓
        Grading model
        ↓
        Question-wise marks
        ↓
        Checked-copy PDF

    Current temporary scope:
        - first 2 pages
        - one extraction call per page
        - recovery disabled
        - grading active
        - grading-review model disabled

    Later, max_pages can be changed to None for full-copy processing.
    """

    def __init__(
        self,
        *,
        page_count_fn: Callable[[str], int],
        render_page_fn: Callable[[str, int], Image.Image],
        extract_page_fn: Callable[..., object],
        aggregation_service: SubmissionAggregationService,
        grading_model: GradingModel,
        checked_copy_renderer: CheckedCopyRenderer | None = None,
        max_pages: int | None = 2,
    ) -> None:
        self.page_count_fn = page_count_fn
        self.render_page_fn = render_page_fn
        self.extract_page_fn = extract_page_fn
        self.aggregation_service = aggregation_service
        self.grading_model = grading_model
        self.checked_copy_renderer = (
            checked_copy_renderer or CheckedCopyRenderer()
        )
        self.max_pages = max_pages

    def run(
        self,
        *,
        pdf_path: str,
        marking_scheme: MarkingScheme,
        job_id: str,
        student_number: str,
        assessment_id: str | None = None,
        expected_question_numbers: list[int] | None = None,
        enable_recovery: bool = False,
        output_dir: str | Path | None = None,
        metadata: dict | None = None,
    ) -> tuple[EvaluationResult, AggregatedSubmission, str]:

        actual_page_count = self.page_count_fn(pdf_path)

        if actual_page_count <= 0:
            raise ValueError("PDF contains no pages.")

        if self.max_pages is None:
            pages_to_process = actual_page_count
        else:
            pages_to_process = min(
                actual_page_count,
                self.max_pages,
            )

        page_results = []
        page_images: list[tuple[int, Image.Image]] = []

        try:
            # ====================================================
            # 1. WHOLE-PAGE EXTRACTION
            # ====================================================

            for page_no in range(1, pages_to_process + 1):

                print("\n" + "=" * 100)
                print(f"GRADING WORKFLOW - EXTRACTION PAGE {page_no}")
                print("=" * 100)

                image = self.render_page_fn(
                    pdf_path,
                    page_no,
                )

                page_images.append(
                    (page_no, image)
                )

                page_result = self.extract_page_fn(
                    image=image,
                    page_no=page_no,
                    expected_question_numbers=(
                        expected_question_numbers or []
                    ),
                    enable_recovery=enable_recovery,
                    feedback=None,
                )

                page_results.append(page_result)

            # ====================================================
            # 2. COMBINE / AGGREGATE
            # ====================================================

            submission = self.aggregation_service.aggregate(
                page_results,
                job_id=job_id,
                student_number=student_number,
                expected_question_numbers=(
                    expected_question_numbers or []
                ),
                metadata={
                    **(metadata or {}),
                    "workflow": "in_memory_grading",
                    "pages_in_current_test": pages_to_process,
                },
            )

            # Keep the original PDF page count distinct from processed pages.
            submission.total_pages = actual_page_count
            submission.processed_pages = pages_to_process
            submission.metadata.update({
                "actual_pdf_pages": actual_page_count,
                "pages_processed": pages_to_process,
                "partial_copy_processing": (
                    pages_to_process < actual_page_count
                ),
            })

            # Never allow a partial answer sheet to proceed to grading.
            if pages_to_process < actual_page_count:
                submission.review_required = True
                partial_warning = (
                    f"Incomplete copy: processed {pages_to_process} of "
                    f"{actual_page_count} PDF pages. Full-copy processing "
                    "is required before grading."
                )
                if partial_warning not in submission.warnings:
                    submission.warnings.append(partial_warning)

            print("\n" + "=" * 100)
            print("COMBINED SUBMISSION")
            print("=" * 100)
            print(
                f"Pages processed: "
                f"{submission.processed_pages}"
            )
            print(
                f"Questions found: "
                f"{len(submission.answers)}"
            )
            # Require explicit teacher review before any grading run.
            if (metadata or {}).get("teacher_approval_required"):
                submission.review_required = True
                approval_warning = (
                    "Teacher approval is required before grading."
                )
                if approval_warning not in submission.warnings:
                    submission.warnings.append(approval_warning)

            print(
                f"Review required: "
                f"{submission.review_required}"
            )

            # Demo-safe preview: fill only genuinely missing questions as unanswered.
            # Conflicting/repeated/unresolved extraction still requires review.
            if (
                submission.missing_questions
                and not submission.repeated_questions
                and not submission.conflicting_questions
                and not int(submission.unresolved_items or 0)
                and not any(
                    getattr(answer, "review_required", False)
                    or str(getattr(answer, "status", "")).upper() in {"REVIEW_REQUIRED", "UNRESOLVED", "FAILED"}
                    for answer in submission.answers
                )
            ):
                _tco_missing_questions = list(submission.missing_questions)
                _tco_answered_numbers = {int(answer.question_no) for answer in submission.answers}
                for _tco_qno in _tco_missing_questions:
                    if int(_tco_qno) not in _tco_answered_numbers:
                        submission.answers.append(AggregatedAnswer(
                            question_no=int(_tco_qno),
                            answer="",
                            confidence=0.0,
                            status="UNANSWERED",
                            review_required=False,
                            warning="No answer was extracted; provisionally treated as unanswered.",
                        ))
                submission.missing_questions = []
                submission.review_required = False
                submission.warnings.append(
                    f"{len(_tco_missing_questions)} missing question(s) provisionally treated as unanswered; teacher approval is required."
                )
            if submission.review_required:
                raise SubmissionReviewRequired(submission)

            # ====================================================
            # 3. GRADING
            # ====================================================

            print("\n" + "=" * 100)
            print("GRADING")
            print("=" * 100)

            evaluation_result = self.grading_model.grade_submission(
                submission=submission,
                marking_scheme=marking_scheme,
                job_id=job_id,
                student_number=student_number,
                assessment_id=assessment_id,
            )

            print(
                f"Obtained marks: "
                f"{evaluation_result.obtained_marks}"
                f" / "
                f"{evaluation_result.total_marks}"
            )

            print(
                f"Percentage: "
                f"{evaluation_result.percentage:.2f}%"
            )

            # ====================================================
            # 4. CHECKED COPY
            # ====================================================

            resolved_output_dir = Path(
                output_dir
                or settings.output_dir
            )

            checked_copy_path = (
                self.checked_copy_renderer.render(
                    page_images=page_images,
                    evaluation_result=evaluation_result,
                    output_dir=resolved_output_dir,
                    file_name=f"{job_id}_checked.pdf",
                )
            )

            print("\n" + "=" * 100)
            print("CHECKED COPY CREATED")
            print("=" * 100)
            print(f"Output: {checked_copy_path}")

            return (
                evaluation_result,
                submission,
                str(checked_copy_path),
            )

        finally:
            for _, image in page_images:
                try:
                    image.close()
                except Exception:
                    pass


# ====================================================================
# FUTURE GRADING REVIEW MODEL
# ====================================================================
#
# DISABLED FOR NOW.
#
# Later:
#
#     Grading Model
#          ↓
#     Grading Review Model
#          ↓
#      ┌───────────┐
#      │           │
#     PASS        FAIL
#      │           │
#      ↓           ↓
# Teacher Review  Re-grade affected questions
#
# Example future implementation:
#
# class GradingReviewModel:
#
#     def review(
#         self,
#         submission: AggregatedSubmission,
#         marking_scheme: MarkingScheme,
#         evaluation_result: EvaluationResult,
#     ) -> dict:
#         ...
#
# This reviewer must remain independent from the grading model.
# ====================================================================
