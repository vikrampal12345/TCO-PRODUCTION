from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from backend.copy_checker.core.config import settings
from backend.copy_checker.services.marking_scheme_importer import load_marking_scheme
from backend.copy_checker.services.in_memory_grading_workflow import SubmissionReviewRequired


class CopyCheckReviewRequired(ValueError):
    """Extraction is uncertain, so the copy must not be graded automatically."""

    def __init__(
        self,
        message: str,
        *,
        submission: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.submission = submission


def _expected_question_numbers_from_scheme(
    scheme: MarkingScheme,
) -> list[int]:
    """Return every question defined by the locked marking scheme."""
    question_numbers = sorted({
        int(question.question_no)
        for question in scheme.questions
    })
    if not question_numbers:
        raise ValueError("The locked marking scheme contains no questions.")
    return question_numbers


def grade_answer_sheet(
    *,
    question_paper_path: str | Path,
    marking_scheme_path: str | Path,
    answer_sheet_path: str | Path,
    job_id: str,
    student_number: str,
    output_dir: str | Path,
    page_limit: int = 2,
    assessment_id: str | None = None,
) -> dict[str, Any]:
    """Run the proven in-memory extraction -> aggregation -> grading -> PDF pipeline.

    The demo deliberately limits processing to pages 1-2. The current extraction
    service does not provide trustworthy per-answer bounding boxes, so the checked
    PDF adds a marking panel alongside each processed page.
    """
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", job_id or ""):
        raise ValueError("Invalid job ID format.")
    if not 1 <= page_limit <= settings.max_pdf_pages:
        raise ValueError(
            f"page_limit must be between 1 and {settings.max_pdf_pages}."
        )

    question_path = Path(question_paper_path)
    scheme_path = Path(marking_scheme_path)
    answer_path = Path(answer_sheet_path)
    for file_path, label in (
        (question_path, "Question paper"),
        (scheme_path, "Marking scheme"),
        (answer_path, "Answer sheet"),
    ):
        if not file_path.is_file():
            raise ValueError(f"{label} file was not found.")

    if question_path.suffix.lower() != ".txt":
        raise ValueError("Question paper must be a .txt file in this demo.")
    if answer_path.suffix.lower() != ".pdf":
        raise ValueError("Answer sheet must be a PDF.")
    if not question_path.read_text(encoding="utf-8-sig").strip():
        raise ValueError("Question paper TXT file is empty.")

    scheme = load_marking_scheme(scheme_path)
    question_types = {
        question.question_no: (
            "mcq" if question.question_type == "mcq" else "subjective"
        )
        for question in scheme.questions
    }
    resolved_student = (student_number or answer_path.stem).strip()
    if not resolved_student or len(resolved_student) > 100:
        raise ValueError("A valid student number is required.")

    # Import model-heavy modules only when a grading run is requested.
    from backend.copy_checker.services.checked_copy_renderer import CheckedCopyRenderer
    from backend.copy_checker.services.grading_model import GradingModel
    from backend.copy_checker.services.in_memory_answer_extraction_service import (
        InMemoryAnswerExtractionService,
    )
    from backend.copy_checker.services.in_memory_grading_workflow import (
        InMemoryGradingWorkflow,
    )
    from backend.copy_checker.services.in_memory_page_processor import (
        InMemoryPageProcessor,
    )
    from backend.copy_checker.services.submission_aggregation_service import (
        SubmissionAggregationService,
    )
    from backend.copy_checker.services.pdf_service import PDFService

    processor = InMemoryPageProcessor()
    pdf_service = PDFService()
    pdf_service.validate_page_count(answer_path, settings.max_pdf_pages)
    actual_page_count = processor.get_page_count(answer_path)
    if actual_page_count <= 0:
        raise ValueError("Answer sheet contains no readable pages.")
    processed_limit = min(page_limit, actual_page_count)

    extractor = InMemoryAnswerExtractionService()
    grader = GradingModel()
    renderer = CheckedCopyRenderer()

    def page_count_fn(path: str) -> int:
        # Report the true PDF length. max_pages separately limits processing.
        return processor.get_page_count(path)

    def render_page_fn(path: str, page_no: int):
        return processor.render_page(path, page_no)

    def extract_page_fn(
        image,
        page_no: int,
        expected_question_numbers: list[int],
        enable_recovery: bool,
        feedback: str | None,
    ):
        # Keep this aligned with the successful two-page live test. The current
        # extractor compares expected questions page-by-page; passing the full
        # paper's question list here can falsely flag questions from other pages.
        return extractor.extract_page_in_memory(
            image=image,
            page_no=page_no,
            expected_question_numbers=[],
            enable_recovery=False,
            feedback=None,
            question_types=question_types,
        )

    workflow = InMemoryGradingWorkflow(
        page_count_fn=page_count_fn,
        render_page_fn=render_page_fn,
        extract_page_fn=extract_page_fn,
        aggregation_service=SubmissionAggregationService(),
        grading_model=grader,
        checked_copy_renderer=renderer,
        max_pages=processed_limit,
    )

    try:
        result, submission, checked_path = workflow.run(
            pdf_path=str(answer_path),
            marking_scheme=scheme,
            job_id=job_id,
            student_number=resolved_student,
            assessment_id=assessment_id or scheme.assessment_id,
            expected_question_numbers=_expected_question_numbers_from_scheme(scheme),
            enable_recovery=False,
            output_dir=output_dir,
            metadata={
                "workflow": "tco_copy_checking_agent",
                "question_paper_provided": True,
                "marking_scheme_status": scheme.status,
                "verification": "disabled_for_demo",
                "grading_review": "disabled_for_demo",
                "page_limit": processed_limit,
                "teacher_approval_required": True,
            },
        )
    except SubmissionReviewRequired as exc:
        raise CopyCheckReviewRequired(
            str(exc),
            submission=exc.submission.model_dump(),
        ) from exc
    except ValueError as exc:
        if "requires review before grading" in str(exc).lower():
            raise CopyCheckReviewRequired(str(exc)) from exc
        raise

    checked_file = Path(checked_path).resolve()
    if not checked_file.is_file():
        raise RuntimeError("Grading completed, but checked-copy PDF was not created.")

    question_wise: list[dict[str, Any]] = []
    for page in result.pages:
        for question in page.get("questions", []):
            question_wise.append({
                "question_no": question["question_no"],
                "marks_awarded": question["marks_awarded"],
                "max_marks": question["max_marks"],
                "reason": question["reason"],
                "confidence": question["confidence"],
                "page": page["page_number"],
            })

    return {
        "status": "success",
        "job_id": job_id,
        "student_number": result.student_id,
        "assessment_id": result.assessment_id,
        "processing": {
            "total_pdf_pages": actual_page_count,
            "pages_processed": result.pages_processed,
            "questions_extracted": len(submission.answers),
            "review_required": submission.review_required,
        },
        "grading": {
            "total_marks": result.total_marks,
            "obtained_marks": result.obtained_marks,
            "percentage": result.percentage,
        },
        "question_wise": question_wise,
        "checked_copy_path": str(checked_file),
        "evaluation_result": result.model_dump(),
        "submission": submission.model_dump(),
    }
