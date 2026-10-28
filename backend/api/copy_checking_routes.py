from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field
from backend.copy_checker.core.config import settings

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

from backend.agents.copy_checking_agent import CopyCheckingAgent
from backend.copy_checker.services.grading_runner import CopyCheckReviewRequired
from backend.copy_checker.services.marking_scheme_importer import MarkingSchemeImportError


router = APIRouter(prefix="/api/v1/copy-checking", tags=["copy-checking"])
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "data" / "copy_checker"
OUTPUT_ROOT = DATA_ROOT / "outputs"
REVIEW_ROOT = DATA_ROOT / "reviews"
MAX_PAPER_BYTES = 5 * 1024 * 1024


class TeacherAnswerCorrection(BaseModel):
    """A teacher-confirmed answer for one marking-scheme question."""

    question_no: int = Field(ge=1)
    answer: str = Field(min_length=1, max_length=20000)


class TeacherAnswerCorrectionsRequest(BaseModel):
    """A batch of answer corrections for a persisted review case."""

    answers: list[TeacherAnswerCorrection] = Field(min_length=1, max_length=100)



class TeacherApprovalRequest(BaseModel):
    """Explicit teacher approval for a saved copy-checking review."""

    teacher_name: str = Field(min_length=2, max_length=120)
    confirm_all_answers_reviewed: bool
    confirm_marking_scheme_locked: bool
    confirmed_blank_questions: list[int] = Field(
        default_factory=list,
        max_length=100,
    )


MAX_SCHEME_BYTES = 5 * 1024 * 1024
MAX_PDF_BYTES = 30 * 1024 * 1024
agent = CopyCheckingAgent()


@lru_cache(maxsize=1)
def _default_registry():
    from backend.core.bootstrap import build_default_registry
    return build_default_registry()


def _execute_registered_task(task, initial_state):
    """Route and execute the copy-checking task on a worker thread."""
    from backend.core.task import Task as TcoTask
    from backend.core.task_router import TaskRouter
    from backend.core.task_executor import TaskExecutor

    if not isinstance(task, TcoTask):
        raise TypeError("Expected a TCO Task.")
    registry = _default_registry()
    provider, routed_task = TaskRouter(registry).route(task)
    return TaskExecutor().execute(provider, routed_task, initial_state)


async def _save_upload(upload: UploadFile, destination: Path, max_bytes: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    try:
        with destination.open("wb") as out:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(status_code=413, detail="Uploaded file exceeds the size limit.")
                out.write(chunk)
    finally:
        await upload.close()
    if size == 0:
        raise HTTPException(status_code=400, detail=f"{upload.filename or 'Uploaded file'} is empty.")




def _persist_copy_checking_result(record: dict[str, Any]) -> None:
    """Persist a completed copy-checking result in the project's SQLite database."""
    import sqlite3

    database_path = Path(__file__).resolve().parents[2] / "data" / "tco.db"
    database_path.parent.mkdir(parents=True, exist_ok=True)

    grading = record.get("grading_result")
    if not isinstance(grading, dict):
        grading = record.get("grading")
    if not isinstance(grading, dict):
        grading = record

    nested_grading = grading.get("grading")
    if not isinstance(nested_grading, dict):
        nested_grading = {}
    evaluation = grading.get("evaluation_result")
    if not isinstance(evaluation, dict):
        evaluation = {}

    def choose_value(key: str):
        for candidate in (grading, nested_grading, evaluation, record):
            value = candidate.get(key) if isinstance(candidate, dict) else None
            if value is not None:
                return value
        return None

    job_id = str(record.get("job_id") or "").strip()
    checked_copy_path = str(record.get("checked_copy_path") or "").strip()
    if not job_id or not checked_copy_path:
        raise ValueError("Cannot persist copy-checking result without job ID and checked-copy path.")

    now = datetime.now(timezone.utc).isoformat()
    created_at = str(record.get("created_at") or now)
    updated_at = str(record.get("updated_at") or record.get("graded_at") or now)

    with sqlite3.connect(database_path, timeout=15) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS copy_checking_results (
                job_id TEXT PRIMARY KEY,
                student_number TEXT,
                status TEXT NOT NULL,
                obtained_marks REAL,
                total_marks REAL,
                percentage REAL,
                checked_copy_path TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        connection.execute("""
            INSERT INTO copy_checking_results (
                job_id, student_number, status, obtained_marks,
                total_marks, percentage, checked_copy_path,
                result_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                student_number = excluded.student_number,
                status = excluded.status,
                obtained_marks = excluded.obtained_marks,
                total_marks = excluded.total_marks,
                percentage = excluded.percentage,
                checked_copy_path = excluded.checked_copy_path,
                result_json = excluded.result_json,
                updated_at = excluded.updated_at
        """, (
            job_id,
            str(record.get("student_number") or ""),
            str(record.get("status") or "success"),
            choose_value("obtained_marks"),
            choose_value("total_marks"),
            choose_value("percentage"),
            checked_copy_path,
            json.dumps({
                "grading_result": grading,
                "teacher_approval": record.get("approval"),
                "job_id": job_id,
            }, ensure_ascii=False, default=str),
            created_at,
            updated_at,
        ))


@router.post("/orchestrated-grade")
async def orchestrated_grade_copy(
    question_paper: UploadFile = File(...),
    marking_scheme: UploadFile = File(...),
    answer_copy: UploadFile = File(...),
    pages: int = Query(
        default=2,
        ge=1,
        le=settings.max_pdf_pages,
        description=(
            "Maximum pages to process, bounded by the configured PDF limit. "
            "If fewer than all PDF pages are processed, grading is blocked."
        ),
    ),
):
    """Upload files and run copy checking through the TCO Master Agent."""
    expected = (
        (question_paper, ".txt", "Question paper must be a .txt file."),
        (marking_scheme, ".txt", "Marking scheme must be a .txt file."),
        (answer_copy, ".pdf", "Student answer copy must be a PDF."),
    )

    for upload, extension, message in expected:
        filename = Path(upload.filename or "").name
        if not filename or Path(filename).suffix.lower() != extension:
            raise HTTPException(status_code=400, detail=message)

    job_id = f"CC-{uuid4().hex[:12]}"
    work_dir = DATA_ROOT / "work" / job_id
    output_dir = OUTPUT_ROOT / job_id
    work_dir.mkdir(parents=True, exist_ok=False)

    paths = {
        "question_paper": work_dir / "question_paper.txt",
        "marking_scheme": work_dir / "marking_scheme.txt",
        "answer_copy": work_dir / "answer_copy.pdf",
    }
    student_number = Path(
        Path(answer_copy.filename or "student.pdf").name
    ).stem

    try:
        await _save_upload(
            question_paper, paths["question_paper"], MAX_PAPER_BYTES
        )
        await _save_upload(
            marking_scheme, paths["marking_scheme"], MAX_SCHEME_BYTES
        )
        await _save_upload(
            answer_copy, paths["answer_copy"], MAX_PDF_BYTES
        )

        # The Master Agent chooses the registered capability/provider.
        from backend.graph import workflow

        initial_state = {
            "teacher_request": (
                "Check the uploaded student's answer sheet using the "
                "provided teacher-approved locked marking scheme."
            ),
            "request_id": job_id,
            "intent": "copy_checking",
            "question_paper_path": str(paths["question_paper"]),
            "marking_scheme_path": str(paths["marking_scheme"]),
            "answer_sheet_path": str(paths["answer_copy"]),
            "student_number": student_number,
            "job_id": job_id,
            "page_limit": pages,
            "assessment_id": None,
            "output_dir": str(output_dir),
            "status": "starting",
            "metadata": {
                "api": "tco-fastapi",
                "source": "master_agent_copy_upload",
                "job_id": job_id,
            },
        }

        state = await run_in_threadpool(
            workflow.invoke, initial_state
        )

        if state.get("status") == "review_required":
            # Persist uploaded inputs before the temporary work folder is removed.
            review_dir = REVIEW_ROOT / job_id
            review_inputs_dir = review_dir / "inputs"
            review_inputs_dir.mkdir(parents=True, exist_ok=False)

            retained_inputs = {}
            for field, source_path in paths.items():
                retained_path = review_inputs_dir / source_path.name
                shutil.copy2(source_path, retained_path)
                retained_inputs[field] = str(
                    Path("inputs") / source_path.name
                )

            review_record = {
                "job_id": job_id,
                "status": "review_required",
                "grading_started": False,
                "student_number": student_number,
                "required_capability": "copy_checking.grade",
                "page_limit": pages,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "reason": (
                    state.get("copy_checking_error")
                    or state.get("clarification_message")
                    or "Teacher review is required before grading."
                ),
                "aggregated_submission": state.get("aggregated_submission"),
                "input_filenames": {
                    "question_paper": Path(
                        question_paper.filename or ""
                    ).name,
                    "marking_scheme": Path(
                        marking_scheme.filename or ""
                    ).name,
                    "answer_copy": Path(
                        answer_copy.filename or ""
                    ).name,
                },
                "retained_inputs": retained_inputs,
                "next_step": (
                    "Review the incomplete extraction. Do not publish marks "
                    "until the complete answer sheet has been checked."
                ),
            }

            (review_dir / "review.json").write_text(
                json.dumps(review_record, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            return JSONResponse(
                status_code=409,
                content={
                    "status": "review_required",
                    "job_id": job_id,
                    "grading_started": False,
                    "message": state.get(
                        "clarification_message",
                        "Teacher review is required before grading.",
                    ),
                    "detail": state.get("copy_checking_error"),
                },
            )

        if state.get("status") in {
            "waiting_for_teacher",
            "needs_clarification",
        }:
            return JSONResponse(
                status_code=409,
                content={
                    "status": state.get("status"),
                    "job_id": job_id,
                    "missing_information": state.get(
                        "missing_information", []
                    ),
                    "message": state.get("clarification_message"),
                },
            )

        if state.get("status") == "error":
            detail = state.get(
                "error_message", "Copy checking failed."
            )
            code = state.get("error_code")
            http_status = (
                400 if code == "COPY_CHECKING_INVALID_INPUT" else 500
            )
            raise HTTPException(
                status_code=http_status,
                detail={
                    "message": detail,
                    "error_code": code,
                    "job_id": job_id,
                },
            )

        outcome = state.get("copy_checking_result")
        if not isinstance(outcome, dict):
            raise HTTPException(
                status_code=500,
                detail="Master Agent returned no Copy Checker grading result.",
            )

        checked_value = state.get("checked_copy_path")
        if not checked_value:
            raise HTTPException(
                status_code=500,
                detail="The checked-copy path was not returned.",
            )

        checked_path = Path(checked_value).resolve()
        resolved_output_dir = output_dir.resolve()

        if not checked_path.is_relative_to(resolved_output_dir):
            raise HTTPException(
                status_code=500,
                detail="Checked-copy output path is outside the job output folder.",
            )

        if not checked_path.is_file():
            raise HTTPException(
                status_code=500,
                detail="The checked-copy PDF was not created.",
            )

        metadata = state.get("metadata") or {}

        direct_record = {
            "job_id": job_id,
            "student_number": student_number,
            "status": "success",
            "grading_result": outcome,
            "checked_copy_path": str(checked_path),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        _persist_copy_checking_result(direct_record)

        return {
            **outcome,
            "status": "success",
            "database_persisted": True,
            "job_id": job_id,
            "student_number": student_number,
            "checked_copy_path": str(checked_path),
            "checked_copy_url": (
                f"/api/v1/copy-checking/jobs/{job_id}/checked-copy"
            ),
            "orchestration": {
                "entrypoint": "master_agent_workflow",
                "required_capability": state.get(
                    "required_capability", "copy_checking.grade"
                ),
                "task_provider": metadata.get("task_provider"),
            },
            "input": {
                "question_paper": Path(
                    question_paper.filename or ""
                ).name,
                "marking_scheme": Path(
                    marking_scheme.filename or ""
                ).name,
                "answer_copy": Path(
                    answer_copy.filename or ""
                ).name,
            },
        }

    except CopyCheckReviewRequired as exc:
        return JSONResponse(
            status_code=409,
            content={
                "status": "review_required",
                "job_id": job_id,
                "grading_started": False,
                "detail": str(exc),
            },
        )
    except MarkingSchemeImportError as exc:
        raise HTTPException(
            status_code=400, detail=str(exc)
        ) from exc
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
        await question_paper.close()
        await marking_scheme.close()
        await answer_copy.close()


@router.post("/grade")
async def grade_copy(
    question_paper: UploadFile = File(...),
    marking_scheme: UploadFile = File(...),
    answer_copy: UploadFile = File(...),
    pages: int = Query(
        default=2,
        ge=1,
        le=settings.max_pdf_pages,
        description=(
            "Maximum pages to process, bounded by the configured PDF limit. "
            "If fewer than all PDF pages are processed, grading is blocked."
        ),
    ),
):
    """Run the local-LLM 2-page demo through the TCO Copy Checking Agent."""
    expected = (
        (question_paper, ".txt", "Question paper must be a .txt file."),
        (marking_scheme, ".txt", "Marking scheme must be a .txt file."),
        (answer_copy, ".pdf", "Student answer copy must be a PDF."),
    )
    for upload, extension, message in expected:
        filename = Path(upload.filename or "").name
        if not filename or Path(filename).suffix.lower() != extension:
            raise HTTPException(status_code=400, detail=message)

    job_id = f"CC-{uuid4().hex[:12]}"
    work_dir = DATA_ROOT / "work" / job_id
    output_dir = OUTPUT_ROOT / job_id
    work_dir.mkdir(parents=True, exist_ok=False)
    paths = {
        "question_paper": work_dir / "question_paper.txt",
        "marking_scheme": work_dir / "marking_scheme.txt",
        "answer_copy": work_dir / "answer_copy.pdf",
    }
    student_number = Path(Path(answer_copy.filename or "student.pdf").name).stem

    try:
        await _save_upload(question_paper, paths["question_paper"], MAX_PAPER_BYTES)
        await _save_upload(marking_scheme, paths["marking_scheme"], MAX_SCHEME_BYTES)
        await _save_upload(answer_copy, paths["answer_copy"], MAX_PDF_BYTES)

        # Invoke the registered TCO specialist, not a second standalone FastAPI app.
        from backend.core.task import Task

        task = Task(
            capability="copy_checking.grade",
            input_data={
                "question_paper_path": str(paths["question_paper"]),
                "marking_scheme_path": str(paths["marking_scheme"]),
                "answer_sheet_path": str(paths["answer_copy"]),
                "student_number": student_number,
                "job_id": job_id,
                "page_limit": pages,
                "assessment_id": None,
                "output_dir": str(output_dir),
            },
            metadata={"source": "fastapi_upload", "demo_page_limit": pages},
        )
        initial_state = {
            "teacher_request": "Check the uploaded student answer sheet using the supplied locked marking scheme.",
            "intent": "copy_checking",
            "required_capability": "copy_checking.grade",
            "status": "task_executing",
            "metadata": {"source": "fastapi_upload"},
        }
        state = await run_in_threadpool(
            _execute_registered_task, task, initial_state
        )

        if state.get("status") == "review_required":
            return JSONResponse(status_code=409, content={
                "status": "review_required",
                "job_id": job_id,
                "grading_started": False,
                "message": state.get("clarification_message", "Teacher review is required before grading."),
                "detail": state.get("copy_checking_error", "Extraction requires review."),
            })
        if state.get("status") == "error":
            detail = state.get("error_message", "Copy checking failed.")
            if state.get("error_code") == "COPY_CHECKING_INVALID_INPUT":
                raise HTTPException(status_code=400, detail=detail)
            raise HTTPException(status_code=500, detail=f"Copy checking failed: {detail}")

        outcome = state.get("copy_checking_result")
        if not isinstance(outcome, dict):
            raise HTTPException(status_code=500, detail="Copy checking agent returned no grading result.")
        checked_path = Path(state.get("checked_copy_path", "")).resolve()
        if not checked_path.is_file():
            raise HTTPException(status_code=500, detail="The checked-copy PDF was not created.")

        return {
            **outcome,
            "input": {
                "question_paper": Path(question_paper.filename or "").name,
                "marking_scheme": Path(marking_scheme.filename or "").name,
                "answer_copy": Path(answer_copy.filename or "").name,
            },
            "checked_copy_url": f"/api/v1/copy-checking/jobs/{job_id}/checked-copy",
        }
    except CopyCheckReviewRequired as exc:
        return JSONResponse(status_code=409, content={
            "status": "review_required", "job_id": job_id,
            "grading_started": False, "detail": str(exc),
        })
    except MarkingSchemeImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
        await question_paper.close()
        await marking_scheme.close()
        await answer_copy.close()



@router.post("/jobs/{job_id}/approve-result")
def approve_copy_checking_result(job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Persist a teacher-approved Copy Checking result after preview."""
    if not re.fullmatch(r"CC-[a-f0-9]{12}", job_id):
        raise HTTPException(status_code=404, detail="Copy checking job not found.")

    grading_result = payload.get("grading_result")
    if not isinstance(grading_result, dict):
        raise HTTPException(status_code=422, detail="A grading result is required for approval.")

    output_dir = (OUTPUT_ROOT / job_id).resolve()
    checked_path = (output_dir / f"{job_id}_checked.pdf").resolve()
    if not checked_path.is_relative_to(output_dir) or not checked_path.is_file():
        raise HTTPException(status_code=404, detail="Checked copy is not ready for approval.")

    timestamp = datetime.now(timezone.utc).isoformat()
    student_number = str(payload.get("student_number") or "").strip()
    record = {
        "job_id": job_id,
        "student_number": student_number,
        "status": "approved",
        "grading_result": grading_result,
        "checked_copy_path": str(checked_path),
        "created_at": timestamp,
        "updated_at": timestamp,
        "approval": {
            "approved": True,
            "approved_at": timestamp,
            "teacher_name": str(payload.get("teacher_name") or "Teacher"),
        },
    }

    try:
        _persist_copy_checking_result(record)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not save approved result: {exc}") from exc

    return {
        "status": "approved",
        "database_persisted": True,
        "job_id": job_id,
        "student_number": student_number,
        "message": "Teacher approved the result and it has been saved to the database.",
    }


@router.get("/jobs/{job_id}/review")
def get_copy_checking_review(job_id: str):
    """Return persisted review metadata for a copy-checking job."""
    if not re.fullmatch(r"CC-[a-f0-9]{12}", job_id):
        raise HTTPException(status_code=404, detail="Review case not found.")

    review_path = REVIEW_ROOT / job_id / "review.json"
    if not review_path.is_file():
        raise HTTPException(status_code=404, detail="Review case not found.")

    try:
        review_record = json.loads(
            review_path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not read the persisted review case.",
        ) from exc

    return review_record



@router.put("/jobs/{job_id}/review/answers")
def update_copy_checking_review_answers(
    job_id: str,
    payload: TeacherAnswerCorrectionsRequest,
):
    """Save teacher corrections without approving or starting grading."""
    if not re.fullmatch(r"CC-[a-f0-9]{12}", job_id):
        raise HTTPException(status_code=404, detail="Review case not found.")

    review_path = REVIEW_ROOT / job_id / "review.json"
    if not review_path.is_file():
        raise HTTPException(status_code=404, detail="Review case not found.")

    try:
        record = json.loads(review_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not read the persisted review case.",
        ) from exc

    if record.get("status") != "review_required":
        raise HTTPException(
            status_code=409,
            detail="This review case is not currently editable.",
        )

    submission = record.get("aggregated_submission")
    if not isinstance(submission, dict):
        raise HTTPException(
            status_code=409,
            detail="This review case has no saved extracted submission.",
        )

    answers = submission.get("answers")
    if not isinstance(answers, list):
        raise HTTPException(
            status_code=409,
            detail="The saved submission has an invalid answers collection.",
        )

    expected = submission.get("expected_questions") or []
    missing = submission.get("missing_questions") or []

    try:
        allowed_numbers = {int(number) for number in expected}
        allowed_numbers.update(int(number) for number in missing)
        for item in answers:
            if not isinstance(item, dict) or "question_no" not in item:
                raise ValueError("Malformed saved answer.")
            allowed_numbers.add(int(item["question_no"]))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail="The saved submission contains invalid question numbers.",
        ) from exc

    corrections = payload.answers
    correction_numbers = [item.question_no for item in corrections]

    if len(set(correction_numbers)) != len(correction_numbers):
        raise HTTPException(
            status_code=422,
            detail="Submit at most one correction per question number.",
        )

    # Validate the entire request before mutating any answers.
    for correction in corrections:
        if correction.question_no not in allowed_numbers:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Question {correction.question_no} is not present "
                    "in the saved submission or marking-scheme question list."
                ),
            )
        if not correction.answer.strip():
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Question {correction.question_no} needs a non-empty "
                    "corrected answer."
                ),
            )

    existing_audit = record.get("teacher_corrections")
    if not isinstance(existing_audit, list):
        existing_audit = []

    timestamp = datetime.now(timezone.utc).isoformat()
    answers_by_number = {
        int(item["question_no"]): item for item in answers
    }

    for correction in corrections:
        question_no = correction.question_no
        corrected_answer = correction.answer.strip()
        answer_record = answers_by_number.get(question_no)
        previous_answer = answer_record.get("answer") if answer_record else None

        if answer_record is None:
            answer_record = {
                "question_no": question_no,
                "answer": corrected_answer,
                "confidence": None,
                "observations": [],
                "status": "TEACHER_CORRECTED",
                "review_required": False,
                "warning": None,
            }
            answers.append(answer_record)
            answers_by_number[question_no] = answer_record
        else:
            answer_record["answer"] = corrected_answer
            answer_record["confidence"] = None
            answer_record["status"] = "TEACHER_CORRECTED"
            answer_record["review_required"] = False
            answer_record["warning"] = None

        existing_audit.append({
            "question_no": question_no,
            "previous_answer": previous_answer,
            "corrected_answer": corrected_answer,
            "corrected_at": timestamp,
        })

    answers.sort(key=lambda item: int(item["question_no"]))

    corrected_numbers = set(correction_numbers)
    submission["missing_questions"] = sorted(
        int(number)
        for number in missing
        if int(number) not in corrected_numbers
    )

    for field in ("conflicting_questions", "repeated_questions"):
        values = submission.get(field) or []
        submission[field] = sorted(
            int(number)
            for number in values
            if int(number) not in corrected_numbers
        )

    # Recalculate unresolved issues after teacher corrections.
    # Count distinct questions, so one question present in multiple issue
    # lists is not counted multiple times.
    outstanding_question_numbers = set()

    for field in (
        "missing_questions",
        "conflicting_questions",
        "repeated_questions",
    ):
        outstanding_question_numbers.update(
            int(number) for number in (submission.get(field) or [])
        )

    for item in answers:
        status = str(item.get("status", "")).upper()
        if (
            item.get("review_required")
            or status in {"REVIEW_REQUIRED", "UNRESOLVED", "FAILED"}
        ):
            outstanding_question_numbers.add(int(item["question_no"]))

    submission["unresolved_items"] = len(outstanding_question_numbers)

    # Explicitly retain the safety gate. These corrections are not an approval.
    submission["review_required"] = True
    record["aggregated_submission"] = submission
    record["teacher_corrections"] = existing_audit
    record["updated_at"] = timestamp
    record["status"] = "review_required"
    record["grading_started"] = False
    record["ready_for_grading"] = False
    record["validation"] = {
        "teacher_corrections_saved": True,
        "full_copy_reprocessed": False,
        "grading_resume_enabled": False,
        "outstanding_extraction_issues": {
            "missing_questions": submission["missing_questions"],
            "conflicting_questions": submission.get("conflicting_questions", []),
            "repeated_questions": submission.get("repeated_questions", []),
            "unresolved_items": submission.get("unresolved_items", 0),
            "answers_still_marked_for_review": [
                int(item["question_no"])
                for item in answers
                if item.get("review_required")
                or str(item.get("status", "")).upper()
                in {"REVIEW_REQUIRED", "UNRESOLVED", "FAILED"}
            ],
        },
    }

    temporary_record = review_path.with_suffix(".json.tmp")
    try:
        temporary_record.write_text(
            json.dumps(record, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary_record.replace(review_path)
    except OSError as exc:
        temporary_record.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail="Could not save the teacher corrections.",
        ) from exc

    return {
        "status": "answers_updated",
        "job_id": job_id,
        "updated_questions": correction_numbers,
        "grading_started": False,
        "ready_for_grading": False,
        "message": (
            "Teacher corrections saved. Full-copy validation and grading "
            "resume are not enabled; the review gate remains active."
        ),
        "validation": record["validation"],
    }




@router.post("/jobs/{job_id}/approve-and-grade")
def approve_and_grade_copy_checking(
    job_id: str,
    payload: TeacherApprovalRequest,
):
    """Validate teacher review, grade the saved submission, and create its PDF."""
    from copy import deepcopy

    from backend.copy_checker.core.config import settings
    from backend.copy_checker.schemas.submission import AggregatedSubmission
    from backend.copy_checker.services.marking_scheme_importer import (
        load_marking_scheme,
    )
    from backend.copy_checker.services.grading_model import GradingModel
    from backend.copy_checker.services.checked_copy_renderer import (
        CheckedCopyRenderer,
    )
    from backend.copy_checker.services.in_memory_page_processor import (
        InMemoryPageProcessor,
    )

    if not re.fullmatch(r"CC-[a-f0-9]{12}", job_id):
        raise HTTPException(status_code=404, detail="Review case not found.")

    if not payload.teacher_name.strip():
        raise HTTPException(
            status_code=422,
            detail="teacher_name cannot be blank.",
        )

    if (
        payload.confirm_all_answers_reviewed is not True
        or payload.confirm_marking_scheme_locked is not True
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Explicit confirmation of the reviewed answers and locked "
                "marking scheme is required."
            ),
        )

    review_dir = (REVIEW_ROOT / job_id).resolve()
    review_path = review_dir / "review.json"

    if not review_path.is_file():
        raise HTTPException(status_code=404, detail="Review case not found.")

    try:
        record = json.loads(review_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not read the saved review case.",
        ) from exc

    if record.get("status") != "review_required":
        raise HTTPException(
            status_code=409,
            detail=(
                "This job is not awaiting approval. "
                "It may already have been graded or may be in progress."
            ),
        )

    if record.get("grading_started") is True:
        raise HTTPException(
            status_code=409,
            detail="Grading has already been started for this job.",
        )

    original_submission = record.get("aggregated_submission")
    if not isinstance(original_submission, dict):
        raise HTTPException(
            status_code=409,
            detail="No saved extracted submission is available.",
        )

    # Work on a copy: failed validation must not mutate the saved review.
    submission_data = deepcopy(original_submission)
    metadata = submission_data.get("metadata") or {}

    total_pages = int(submission_data.get("total_pages") or 0)
    processed_pages = int(submission_data.get("processed_pages") or 0)

    if (
        metadata.get("partial_copy_processing") is True
        or total_pages <= 0
        or processed_pages != total_pages
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Full-copy processing is required before grading. "
                f"Reported total pages={total_pages}, "
                f"processed pages={processed_pages}."
            ),
        )

    # Resolve only genuinely missing questions as explicitly blank.
    blanks_list = payload.confirmed_blank_questions
    blank_questions = set(blanks_list)

    if len(blank_questions) != len(blanks_list):
        raise HTTPException(
            status_code=400,
            detail="confirmed_blank_questions contains duplicates.",
        )

    expected_from_submission = {
        int(number)
        for number in submission_data.get("expected_questions", [])
    }
    missing = {
        int(number)
        for number in submission_data.get("missing_questions", [])
    }
    conflicting = {
        int(number)
        for number in submission_data.get("conflicting_questions", [])
    }
    repeated = {
        int(number)
        for number in submission_data.get("repeated_questions", [])
    }

    if not blank_questions.issubset(missing):
        raise HTTPException(
            status_code=400,
            detail=(
                "A question can be confirmed blank through this request "
                "only when it is currently listed as missing."
            ),
        )

    if blank_questions.intersection(conflicting | repeated):
        raise HTTPException(
            status_code=409,
            detail=(
                "Conflicting or repeated answers must be explicitly corrected "
                "before a blank answer can be confirmed."
            ),
        )

    # Fail fast: unresolved answers must be rejected before file access.
    # This also keeps the review endpoint predictable for incomplete cases.
    try:
        preliminary_missing = {
            int(number)
            for number in submission_data.get("missing_questions", [])
        }
        preliminary_conflicting = {
            int(number)
            for number in submission_data.get("conflicting_questions", [])
        }
        preliminary_repeated = {
            int(number)
            for number in submission_data.get("repeated_questions", [])
        }
        preliminary_blanks_list = [
            int(number) for number in payload.confirmed_blank_questions
        ]
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail="Saved review contains invalid question numbers.",
        ) from exc

    preliminary_blanks = set(preliminary_blanks_list)

    if len(preliminary_blanks) != len(preliminary_blanks_list):
        raise HTTPException(
            status_code=400,
            detail="confirmed_blank_questions contains duplicates.",
        )

    if not preliminary_blanks.issubset(preliminary_missing):
        raise HTTPException(
            status_code=400,
            detail=(
                "A question can be confirmed blank through this request "
                "only when it is currently listed as missing."
            ),
        )

    if preliminary_blanks.intersection(
        preliminary_conflicting | preliminary_repeated
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Conflicting or repeated answers must be corrected before "
                "a blank answer can be confirmed."
            ),
        )

    outstanding_missing = preliminary_missing - preliminary_blanks

    if (
        outstanding_missing
        or preliminary_conflicting
        or preliminary_repeated
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "message": (
                    "Resolve all missing, conflicting, and repeated questions "
                    "before approval."
                ),
                "missing_questions": sorted(outstanding_missing),
                "conflicting_questions": sorted(preliminary_conflicting),
                "repeated_questions": sorted(preliminary_repeated),
            },
        )

    retained_inputs = record.get("retained_inputs") or {}

    def retained_input_path(field: str) -> Path:
        relative_value = retained_inputs.get(field)
        if not isinstance(relative_value, str) or not relative_value:
            raise HTTPException(
                status_code=409,
                detail=f"The retained {field} file is missing from this review.",
            )

        candidate = (review_dir / relative_value).resolve()
        if not candidate.is_relative_to(review_dir):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid retained path for {field}.",
            )
        if not candidate.is_file():
            raise HTTPException(
                status_code=409,
                detail=f"The retained {field} file cannot be found.",
            )
        return candidate

    question_path = retained_input_path("question_paper")
    scheme_path = retained_input_path("marking_scheme")
    answer_path = retained_input_path("answer_copy")

    if question_path.suffix.lower() != ".txt":
        raise HTTPException(
            status_code=409,
            detail="The retained question paper must be a TXT file.",
        )
    if answer_path.suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=409,
            detail="The retained answer copy must be a PDF.",
        )

    try:
        scheme = load_marking_scheme(scheme_path)
    except Exception as exc:
        raise HTTPException(
            status_code=409,
            detail=f"The retained marking scheme could not be loaded: {exc}",
        ) from exc

    if getattr(scheme, "status", None) != "locked":
        raise HTTPException(
            status_code=409,
            detail="Grading requires the teacher-approved locked marking scheme.",
        )

    expected_numbers = sorted({
        int(question.question_no)
        for question in scheme.questions
    })
    expected_set = set(expected_numbers)

    if not expected_set:
        raise HTTPException(
            status_code=409,
            detail="The locked marking scheme contains no questions.",
        )

    if expected_from_submission and expected_from_submission != expected_set:
        raise HTTPException(
            status_code=409,
            detail=(
                "The saved submission's expected questions do not match "
                "the locked marking scheme. Reconcile the review first."
            ),
        )

    if not blank_questions.issubset(expected_set):
        raise HTTPException(
            status_code=400,
            detail="A blank confirmation references an unknown question.",
        )

    # A confirmed blank is stored as a null answer. GradingModel already
    # interprets a missing/null answer as [NO ANSWER].
    answers = submission_data.get("answers")
    if not isinstance(answers, list):
        raise HTTPException(
            status_code=409,
            detail="The saved answers collection is invalid.",
        )

    answer_map = {}
    for answer in answers:
        if not isinstance(answer, dict):
            raise HTTPException(
                status_code=409,
                detail="The saved submission contains an invalid answer record.",
            )
        try:
            number = int(answer["question_no"])
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=409,
                detail="An answer record has an invalid question number.",
            ) from exc

        if number in answer_map:
            raise HTTPException(
                status_code=409,
                detail=f"Duplicate saved answer records exist for Q{number}.",
            )
        if number not in expected_set:
            raise HTTPException(
                status_code=409,
                detail=f"Saved submission contains unexpected question Q{number}.",
            )
        answer_map[number] = answer

    for number in sorted(blank_questions):
        if number in answer_map:
            existing_answer = answer_map[number].get("answer")
            if str(existing_answer or "").strip():
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Q{number} already has a non-empty saved answer. "
                        "Edit or resolve it before confirming it blank."
                    ),
                )

            answer_map[number].update({
                "answer": None,
                "confidence": None,
                "observations": [],
                "status": "TEACHER_CONFIRMED_BLANK",
                "review_required": False,
                "warning": "Teacher explicitly confirmed that this answer is blank.",
            })
        else:
            blank_record = {
                "question_no": number,
                "answer": None,
                "confidence": None,
                "observations": [],
                "status": "TEACHER_CONFIRMED_BLANK",
                "review_required": False,
                "warning": "Teacher explicitly confirmed that this answer is blank.",
            }
            answers.append(blank_record)
            answer_map[number] = blank_record

    missing -= blank_questions

    # Never bypass repeated/conflicting flags. The correction endpoint must
    # first record teacher-corrected values and clear the applicable flags.
    if missing or conflicting or repeated:
        raise HTTPException(
            status_code=409,
            detail={
                "message": (
                    "Resolve all missing, conflicting, and repeated questions "
                    "before approval."
                ),
                "missing_questions": sorted(missing),
                "conflicting_questions": sorted(conflicting),
                "repeated_questions": sorted(repeated),
            },
        )

    unresolved_answer_numbers = sorted(
        int(answer["question_no"])
        for answer in answers
        if answer.get("review_required")
        or str(answer.get("status", "")).upper()
        in {"REVIEW_REQUIRED", "UNRESOLVED", "FAILED"}
    )
    if unresolved_answer_numbers:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Some answer records still require review.",
                "questions": unresolved_answer_numbers,
            },
        )

    actual_answer_numbers = set(answer_map)
    uncovered = expected_set - actual_answer_numbers
    if uncovered:
        raise HTTPException(
            status_code=409,
            detail={
                "message": (
                    "Every expected question must have a teacher-reviewed answer "
                    "or an explicit blank confirmation."
                ),
                "questions_without_resolution": sorted(uncovered),
            },
        )

    if actual_answer_numbers != expected_set:
        raise HTTPException(
            status_code=409,
            detail="The saved answer records do not match the locked marking scheme.",
        )

    # All question-level checks are clear now. Recompute the derived unresolved
    # count rather than carrying a stale aggregation count after teacher edits.
    submission_data["answers"] = sorted(
        answers,
        key=lambda item: int(item["question_no"]),
    )
    submission_data["expected_questions"] = expected_numbers
    submission_data["missing_questions"] = []
    submission_data["conflicting_questions"] = []
    submission_data["repeated_questions"] = []
    submission_data["unresolved_items"] = 0
    submission_data["review_required"] = False
    submission_data["metadata"] = {
        **metadata,
        "partial_copy_processing": False,
        "teacher_approval_required": False,
        "teacher_approved": True,
    }

    historical_warning_prefixes = (
        "Missing expected questions:",
        "Repeated question numbers detected:",
        "Conflicting observations detected for questions:",
        "Incomplete copy:",
        "Teacher approval is required before grading.",
    )
    submission_data["warnings"] = [
        warning
        for warning in submission_data.get("warnings", [])
        if not str(warning).startswith(historical_warning_prefixes)
    ]

    try:
        approved_submission = AggregatedSubmission.model_validate(
            submission_data
        )
    except Exception as exc:
        raise HTTPException(
            status_code=409,
            detail=f"The reviewed submission failed schema validation: {exc}",
        ) from exc

    # Re-check the retained PDF itself: do not trust the saved page count alone.
    try:
        processor = InMemoryPageProcessor()
        actual_pages = processor.get_page_count(str(answer_path))
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"The retained answer PDF could not be read: {exc}",
        ) from exc

    if actual_pages <= 0 or actual_pages > settings.max_pdf_pages:
        raise HTTPException(
            status_code=409,
            detail=(
                f"PDF page count {actual_pages} is invalid or exceeds the "
                f"configured limit {settings.max_pdf_pages}."
            ),
        )

    if actual_pages != total_pages or actual_pages != processed_pages:
        raise HTTPException(
            status_code=409,
            detail=(
                "The retained PDF's page count differs from the saved "
                "processed submission. Reprocess the complete copy first."
            ),
        )

    # Persist the explicit approval and an in-progress status before invoking
    # the grading model, so a subsequent ordinary request cannot re-grade a
    # job that is no longer in review_required state.
    timestamp = datetime.now(timezone.utc).isoformat()
    record["status"] = "grading_in_progress"
    record["grading_started"] = True
    record["ready_for_grading"] = False
    record["aggregated_submission"] = approved_submission.model_dump()
    record["approval"] = {
        "approved": True,
        "teacher_name": payload.teacher_name.strip(),
        "approved_at": timestamp,
        "confirmed_all_answers_reviewed": True,
        "confirmed_marking_scheme_locked": True,
        "confirmed_blank_questions": sorted(blank_questions),
    }
    record["updated_at"] = timestamp

    def persist_record():
        temporary_record = review_path.with_suffix(".json.tmp")
        temporary_record.write_text(
            json.dumps(record, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary_record.replace(review_path)

    try:
        persist_record()
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not persist the teacher approval record.",
        ) from exc

    page_images = []
    try:
        grader = GradingModel()
        evaluation = grader.grade_submission(
            submission=approved_submission,
            marking_scheme=scheme,
            job_id=job_id,
            student_number=(
                record.get("student_number")
                or answer_path.stem
            ),
            assessment_id=getattr(scheme, "assessment_id", None),
        )

        for page_no in range(1, actual_pages + 1):
            image = processor.render_page(str(answer_path), page_no)
            page_images.append((page_no, image))

        job_output_dir = (OUTPUT_ROOT / job_id).resolve()
        output_root_resolved = OUTPUT_ROOT.resolve()
        if not job_output_dir.is_relative_to(output_root_resolved):
            raise ValueError("Unsafe checked-copy output directory.")

        job_output_dir.mkdir(parents=True, exist_ok=True)
        checked_path = CheckedCopyRenderer().render(
            page_images=page_images,
            evaluation_result=evaluation,
            output_dir=job_output_dir,
            file_name=f"{job_id}_checked.pdf",
        )

        checked_path = Path(checked_path).resolve()
        if not checked_path.is_relative_to(job_output_dir):
            raise ValueError("Checked-copy output escaped the job directory.")
        if not checked_path.is_file():
            raise RuntimeError("The checked-copy PDF was not created.")

        question_wise = []
        for page in evaluation.pages:
            for question in page.get("questions", []):
                question_wise.append({
                    "question_no": question["question_no"],
                    "marks_awarded": question["marks_awarded"],
                    "max_marks": question["max_marks"],
                    "reason": question["reason"],
                    "confidence": question["confidence"],
                    "page": page["page_number"],
                })

        grading_summary = {
            "total_marks": evaluation.total_marks,
            "obtained_marks": evaluation.obtained_marks,
            "percentage": evaluation.percentage,
            "question_wise": question_wise,
            "evaluation_result": evaluation.model_dump(),
            "checked_copy_url": (
                f"/api/v1/copy-checking/jobs/{job_id}/checked-copy"
            ),
        }

        record["status"] = "success"
        record["grading_started"] = True
        record["ready_for_grading"] = False
        record["graded_at"] = datetime.now(timezone.utc).isoformat()
        record["grading_result"] = grading_summary
        record["checked_copy_path"] = str(checked_path)
        record["aggregated_submission"] = approved_submission.model_dump()
        record["updated_at"] = record["graded_at"]
        persist_record()
        _persist_copy_checking_result(record)

        return {
            "status": "success",
            "database_persisted": True,
            "job_id": job_id,
            "teacher_approval": record["approval"],
            "grading": {
                "total_marks": evaluation.total_marks,
                "obtained_marks": evaluation.obtained_marks,
                "percentage": evaluation.percentage,
            },
            "question_wise": question_wise,
            "checked_copy_url": (
                f"/api/v1/copy-checking/jobs/{job_id}/checked-copy"
            ),
            "message": (
                "Teacher approval recorded. Grading completed using the "
                "saved teacher-reviewed answers."
            ),
        }

    except Exception as exc:
        # Preserve the review record, but do not advertise a failed grading run
        # as a completed result.
        record["status"] = "grading_failed"
        record["grading_started"] = False
        record["ready_for_grading"] = False
        record["grading_error"] = str(exc)
        record["updated_at"] = datetime.now(timezone.utc).isoformat()
        try:
            persist_record()
        except OSError:
            pass

        raise HTTPException(
            status_code=500,
            detail=(
                "Grading or checked-copy generation failed. The review record "
                "was retained; inspect grading_error before retrying."
            ),
        ) from exc

    finally:
        for _, image in page_images:
            try:
                image.close()
            except Exception:
                pass



@router.get("/jobs/{job_id}/checked-copy")
def download_checked_copy(job_id: str):
    if not re.fullmatch(r"CC-[a-f0-9]{12}", job_id):
        raise HTTPException(status_code=404, detail="Checked copy not found.")
    path = OUTPUT_ROOT / job_id / f"{job_id}_checked.pdf"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Checked copy not found.")
    return FileResponse(path, media_type="application/pdf", filename=path.name, content_disposition_type="inline")
