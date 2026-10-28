from __future__ import annotations

from typing import Any

from backend.core.base_agent import BaseAgent
from backend.core.task import Task
from backend.state import TCOState
from backend.copy_checker.services.grading_runner import (
    CopyCheckReviewRequired,
    grade_answer_sheet,
)


class CopyCheckingAgent(BaseAgent):
    """TCO specialist for extracting, grading, and rendering answer-sheet copies."""

    name = "copy_checking_agent"
    description = (
        "Extracts answers from uploaded handwritten PDF copies, grades them against "
        "a locked teacher marking scheme, and creates a checked-copy PDF."
    )
    capabilities = ("copy_checking.grade",)

    def run(
        self,
        state: TCOState,
        task: Task | dict[str, Any] | None = None,
    ) -> TCOState:
        task_input: dict[str, Any] = {}
        if isinstance(task, Task):
            task_input = task.input_data
        elif isinstance(task, dict):
            task_input = task.get("input_data", task)

        def supplied(name: str, default: Any = None) -> Any:
            return task_input.get(name) or state.get(name) or default

        question_paper_path = supplied("question_paper_path")
        marking_scheme_path = supplied("marking_scheme_path")
        answer_sheet_path = supplied("answer_sheet_path")
        if not all((question_paper_path, marking_scheme_path, answer_sheet_path)):
            return {
                **state,
                "status": "waiting_for_teacher",
                "next_action": "ask_teacher",
                "missing_information": [
                    name for name, value in (
                        ("question_paper", question_paper_path),
                        ("locked_marking_scheme", marking_scheme_path),
                        ("student_answer_sheet_pdf", answer_sheet_path),
                    ) if not value
                ],
                "clarification_message": (
                    "To check copies, please provide the question paper, "
                    "the teacher-approved locked marking scheme, and the student's PDF answer sheet."
                ),
            }

        job_id = str(supplied("job_id", "TCO-COPY-CHECK"))
        student_number = str(
            supplied("student_number") or str(answer_sheet_path).rsplit("/", 1)[-1].rsplit("\\", 1)[-1].rsplit(".", 1)[0]
        )
        try:
            result = grade_answer_sheet(
                question_paper_path=question_paper_path,
                marking_scheme_path=marking_scheme_path,
                answer_sheet_path=answer_sheet_path,
                job_id=job_id,
                student_number=student_number,
                output_dir=supplied("output_dir", "data/copy_checker/outputs"),
                page_limit=int(supplied("page_limit", 2)),
                assessment_id=supplied("assessment_id"),
            )
        except CopyCheckReviewRequired as exc:
            return {
                **state,
                "status": "review_required",
                "grading_started": False,
                "aggregated_submission": exc.submission,
                "copy_checking_error": str(exc),
                "clarification_message": (
                    "The extracted answers need teacher review before grading can continue."
                ),
            }
        except ValueError as exc:
            return {
                **state,
                "status": "error",
                "error_code": "COPY_CHECKING_INVALID_INPUT",
                "error_message": str(exc),
            }
        except Exception as exc:
            return {
                **state,
                "status": "error",
                "error_code": "COPY_CHECKING_FAILED",
                "error_message": str(exc),
            }

        return {
            **state,
            "status": "graded",
            "copy_checking_result": {
                key: value for key, value in result.items()
                if key not in {"evaluation_result", "submission"}
            },
            "evaluation_result": result["evaluation_result"],
            "aggregated_submission": result["submission"],
            "checked_copy_path": result["checked_copy_path"],
            "next_action": "end",
        }
